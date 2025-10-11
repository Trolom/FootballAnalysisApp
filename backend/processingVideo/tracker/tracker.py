from ultralytics import YOLO
import supervision as sv
import pickle
import os
import sys
sys.path.append('../')
from ..utils import get_center_of_bbox, get_foot_position, draw_ellipse, draw_triangle, measure_distance, draw_team_ball_control
import cv2
import numpy as np
import pandas as pd

class Tracker:
    def __init__(self, model_path: str = 'models/player_detection.pt'):
        self.model = YOLO(model_path)
        self.tracker = sv.ByteTrack()
        self.max_player_ball_distance = 70



    def add_position_to_track(self, tracks):
        for obj, obj_tracks in tracks.items():
            for frame_num, track in enumerate(obj_tracks):
                for track_id, info in track.items():
                    box = info.get('bbox')
                    if box is None or len(box) != 4:
                        continue
                    if obj == 'ball':
                        pos = get_center_of_bbox(box)
                    else:
                        pos = get_foot_position(box)
                    info['position'] = pos
        

    def detect_frames(self, frames, batch_size=24, conf=0.2, min_bs=1):
        detections = []
        i = 0
        n = len(frames)

        while i < n:
            bs = min(batch_size, n - i)  # cap at remaining frames

            while bs >= min_bs:
                try:
                    batch = frames[i:i+bs]
                    outs = self.model.predict(batch, conf=conf, verbose=False)
                    detections.extend(outs)
                    i += bs
                    break  # processed this chunk, move to next
                except RuntimeError as e:
                    # Typical PyTorch CUDA OOM path
                    if "out of memory" in str(e).lower():
                        # try smaller batch next
                        try:
                            import torch
                            torch.cuda.empty_cache()
                        except Exception:
                            pass
                        bs = max(min_bs, bs // 2)
                        if bs == min_bs:
                            # if we’re already at min and still OOM, retry once more;
                            # if it fails again, re-raise below
                            continue
                    else:
                        raise
            else:
                # We exhausted the inner loop (even min_bs failed)
                raise RuntimeError("detect_frames: OOM even at min batch size.")

        return detections
            

    def get_object_tracks(self, frames):
        detections = self.detect_frames(frames)

        tracks = {
            'players': [],
            'goalkeepers': [],
            'referees': [],
            'ball': []
        }

        cls_names = getattr(self.model, "names", None)

        # Loop through each frame
        for frame_num, detection in enumerate(detections):
            detection_supervision = sv.Detections.from_ultralytics(detection)
            detection_with_tracks = self.tracker.update_with_detections(detection_supervision)

            tracks['players'].append({})
            tracks['goalkeepers'].append({})
            tracks['referees'].append({})
            tracks['ball'].append({})

            for frame_detection in detection_with_tracks:
                bbox = frame_detection[0].tolist()
                cls_id = frame_detection[3]
                track_id = frame_detection[4]

                # Store tracking info based on class type
                if cls_names[cls_id] == 'player':
                    tracks['players'][frame_num][track_id] = {'bbox': bbox}
                elif cls_names[cls_id] == 'goalkeeper':
                    tracks['goalkeepers'][frame_num][track_id] = {'bbox': bbox}
                elif cls_names[cls_id] == 'referee':
                    tracks['referees'][frame_num][track_id] = {'bbox': bbox}

            for frame_detection in detection_supervision:
                bbox = frame_detection[0].tolist()
                cls_id = frame_detection[3]

                if cls_names[cls_id] == 'ball':
                    tracks['ball'][frame_num][1] = {'bbox': bbox}

        return tracks


    def interpolate_ball_positions(self, ball_tracks, box_size=(20,20)):
        """
        ball_tracks: list of per-frame dicts, each {track_id: {'bbox': [x1,y1,x2,y2]}}
        box_size:    (w,h) to re-create a box around the interpolated center
        
        Returns: list of per-frame dicts {1: {'bbox': [x1,y1,x2,y2]}}
        """
        N = len(ball_tracks)
        cx = np.full(N, np.nan, dtype=float)
        cy = np.full(N, np.nan, dtype=float)
        
        # 1) pull out center or nan
        for i, d in enumerate(ball_tracks):
            info = d.get(1)
            if info and 'bbox' in info:
                x1,y1,x2,y2 = info['bbox']
                cx[i] = (x1 + x2) / 2
                cy[i] = (y1 + y2) / 2

        # 2) which frames we actually saw
        idx = np.arange(N)
        seen = ~np.isnan(cx)
        if seen.sum() >= 2:
            # linear interp on each axis
            cx = np.interp(idx, idx[seen], cx[seen])
            cy = np.interp(idx, idx[seen], cy[seen])
        # else, leave as is (all NaN or single point)

        # 3) re-create boxes of fixed size around each center
        w, h = box_size
        half_w, half_h = w/2, h/2
        out = []
        for x, y in zip(cx, cy):
            if not np.isnan(x):
                x1 = x - half_w; x2 = x + half_w
                y1 = y - half_h; y2 = y + half_h
                out.append({1:{'bbox':[x1, y1, x2, y2]}})
            else:
                out.append({})  # no box at all
        return out

    def assign_ball_to_player(self, players: dict[int, dict], ball_bbox: list[float]):
        """
        Return the ID of the player whose foot is closest to ball_bbox,
        but only if that distance ≤ self.max_player_ball_distance.
        Otherwise return None.
        """
        ball_x, ball_y = get_center_of_bbox(ball_bbox)

        best_id, best_d = None, float('inf')
        for pid, info in players.items():
            fx, fy = get_foot_position(info['bbox'])
            d = measure_distance((fx, fy), (ball_x, ball_y))
            if d < best_d:
                best_d, best_id = d, pid

        if best_d <= self.max_player_ball_distance:
            return best_id
        return None


    def draw_annotations(self, video_frames, tracks):
        output_video_frames = []
        team_ball_control = []
        tracks['ball'] = self.interpolate_ball_positions(tracks['ball'])
        for frame_num, frame in enumerate(video_frames):
            frame = frame.copy()

            player_dict = tracks['players'][frame_num]
            goalkeeper_dict = tracks['goalkeepers'][frame_num]
            referee_dict = tracks['referees'][frame_num]
            ball_dict = tracks['ball'][frame_num]

            for p in player_dict.values():
                p['has_ball'] = False
            for g in goalkeeper_dict.values():
                g['has_ball'] = False

            # --- 1) assign ball to player ---
            ball_info = ball_dict.get(1)
            
            assigned = self.assign_ball_to_player(player_dict, ball_info['bbox'])
            if assigned is not None:
                # mark that player
                player_dict[assigned]['has_ball'] = True
                team_ball_control.append(player_dict[assigned]['team'])
            else:
                # no new assignment: repeat last known
                last = team_ball_control[-1] if team_ball_control else None
                team_ball_control.append(last)



            # --- 2) draw players ---
            for track_id, player in player_dict.items():
                color = player.get('team_color', (0, 0, 255))
                frame = draw_ellipse(frame, player['bbox'], color, track_id)

                if player.get('has_ball', False):
                    frame = draw_triangle(frame, player['bbox'], (0, 0, 255))

            # --- 3) draw goalkeepers ---
            for track_id, goalkeeper in goalkeeper_dict.items():
                color = goalkeeper.get('team_color', (0, 0, 255))
                frame = draw_ellipse(frame, goalkeeper['bbox'], color, track_id)

                if goalkeeper.get('has_ball', False):
                    frame = draw_triangle(frame, goalkeeper['bbox'], (0, 0, 255))

            # --- 4) draw referees ---
            for track_id, referee in referee_dict.items():
                frame = draw_ellipse(frame, referee['bbox'], (0, 255, 255))
            
            # --- 5) draw the raw ball if you like (optional) ---
            for track_id, ball in ball_dict.items():
                frame = draw_triangle(frame, ball['bbox'], (0, 255, 0))

            frame = draw_team_ball_control(frame, frame_num, team_ball_control)
            output_video_frames.append(frame)
        
        return output_video_frames

