import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLO
from .homography import ViewTransformer  # keep your import
from . import SoccerPitchConfiguration, draw_pitch, draw_points_on_pitch, draw_pitch_voronoi_diagram_2

class PitchAnnotator:
    def __init__(
        self,
        CONFIG: SoccerPitchConfiguration, 
        conf: float = 0.3,
        model_path: str = "/models/field_detection.pt",  # local YOLO weights
    ):
        # Load local Ultralytics model
        self.model = YOLO(model_path)
        self.conf = float(conf)

        # static pitch schema (in model coordinates)
        self.vertices = np.array(CONFIG.vertices, dtype=np.float32)  # shape (V,2)
        self.edges = CONFIG.edges

        # Supervision annotators for vertices and edges
        self.vertex_annotator = sv.VertexAnnotator(
            color=sv.Color.from_hex("#FF1493"),
            radius=6
        )
        self.edge_annotator = sv.EdgeAnnotator(
            color=sv.Color.from_hex("#000FFF"),
            thickness=2,
            edges=self.edges
        )

        self.BASE_PITCH = draw_pitch(CONFIG)

    def annotate_video_batched(self, video_frames: list[np.ndarray], batch_size: int = 16):
            # 1) batched inference
            results_all = []
            for s in range(0, len(video_frames), batch_size):
                chunk = video_frames[s:s+batch_size]
                # one GPU call for the whole chunk
                res_list = self.model.predict(chunk, conf=self.conf, verbose=False)
                results_all.extend(res_list)
            
            return results_all

    def annotate_frame_from_result(
        self,
        frame: np.ndarray,
        result,
        kp_thresh: float = 0.5
    ) -> np.ndarray:
        canvas = frame.copy()

        # 1) keypoints from precomputed Ultralytics result
        kps = sv.KeyPoints.from_ultralytics(result)
        if kps.xy is None or len(kps.xy) == 0 or kps.xy[0] is None:
            return canvas

        all_pts = kps.xy[0]  # (K,2)
        if all_pts.size == 0:
            return canvas

        # confidences (fallback to ones)
        confidences = (
            kps.confidence[0].astype(np.float32)
            if (kps.confidence is not None and len(kps.confidence) > 0 and kps.confidence[0] is not None)
            else np.ones((all_pts.shape[0],), dtype=np.float32)
        )

        # 2) correspondences (model/pitch -> image)
        K = min(len(self.vertices), len(all_pts))
        if K == 0:
            return canvas

        mask = (confidences[:K] > kp_thresh)
        src_pts = self.vertices[:K][mask]                 # model-space
        dst_pts = all_pts[:K][mask]                        # image-space

        # 3) homography + draw if we have enough pairs
        if src_pts.shape[0] >= 4:
            transformer = ViewTransformer(
                source=src_pts.astype(np.float32),
                target=dst_pts.astype(np.float32)
            )
            frame_all_points = transformer.transform_points(self.vertices.astype(np.float32))
            kp_all = sv.KeyPoints(xy=frame_all_points[np.newaxis, ...])

            canvas = self.edge_annotator.annotate(scene=canvas, key_points=kp_all)
            canvas = self.vertex_annotator.annotate(scene=canvas, key_points=kp_all)

        return canvas

    def transform_positions(self, track_dict, transformer): # helper function
            # track_dict: {id: {'position': (x,y), ...}, ...}
            pts = np.array([info["position"] for info in track_dict.values()], dtype=np.float32)
            if pts.size:
                return transformer.transform_points(points=pts)
            return np.empty((0, 2), dtype=np.float32)
    

    def annotate_tactical_board_from_result(
        self,
        frame: np.ndarray,
        tracks: dict,
        frame_idx: int,
        CONFIG,
        result,
        kp_thresh: float = 0.5,
    ) -> np.ndarray:
        
        # 1) keypoints from Ultralytics result
        key_points = sv.KeyPoints.from_ultralytics(result)
        if key_points.xy is None or len(key_points.xy) == 0 or key_points.xy[0] is None:
            return self.BASE_PITCH.copy()

        xy = key_points.xy[0]
        if xy.size == 0:
            return self.BASE_PITCH.copy()

        conf = (
            key_points.confidence[0].astype(np.float32)
            if (key_points.confidence is not None and len(key_points.confidence) > 0 and key_points.confidence[0] is not None)
            else np.ones((len(xy),), np.float32)
        )

        # 2) image -> pitch correspondences
        mask = conf > kp_thresh
        src_pts = xy[mask]
        dst_pts = np.array(CONFIG.vertices, dtype=np.float32)[mask]
        if src_pts.shape[0] < 4:
            return self.BASE_PITCH.copy()

        transformer = ViewTransformer(source=src_pts.astype(np.float32),
                                    target=dst_pts.astype(np.float32))

        # 3) transform tracks
        ball_dict    = tracks["ball"][frame_idx]
        player_dict  = tracks["players"][frame_idx]
        referee_dict = tracks["referees"][frame_idx]

        pitch_ball    = self.transform_positions(ball_dict, transformer)
        pitch_players = self.transform_positions(player_dict, transformer)
        pitch_refs    = self.transform_positions(referee_dict, transformer)

        # 4) draw on cached base
        board = self.BASE_PITCH.copy()

        board = draw_points_on_pitch(
            config=CONFIG,
            xy=pitch_ball,
            face_color=sv.Color.WHITE,
            edge_color=sv.Color.BLACK,
            radius=10,
            thickness=2,
            pitch=board,
        )

        player_colors = [info["team_color"] for info in player_dict.values()]
        buckets = {}
        for idx, color in enumerate(player_colors):
            buckets.setdefault(tuple(color), []).append(idx)

        for (b, g, r), indices in buckets.items():
            pts = pitch_players[indices] if pitch_players.size else np.empty((0, 2), np.float32)
            board = draw_points_on_pitch(
                config=CONFIG,
                xy=pts,
                face_color=sv.Color(r=r, g=g, b=b),
                edge_color=sv.Color.BLACK,
                radius=16,
                thickness=2,
                pitch=board,
            )

        board = draw_points_on_pitch(
            config=CONFIG,
            xy=pitch_refs,
            face_color=sv.Color.from_hex("FFD700"),
            edge_color=sv.Color.BLACK,
            radius=16,
            thickness=2,
            pitch=board,
        )

        return board


    def annotate_voronoi_from_result(
        self,
        frame: np.ndarray,
        tracks: dict,
        frame_idx: int,
        CONFIG,
        result,
        kp_thresh: float = 0.5,
        vor_step: int = 3,   # 2–4 is a good speed/quality tradeoff
    ) -> np.ndarray:
        key_points = sv.KeyPoints.from_ultralytics(result)
        if key_points.xy is None or len(key_points.xy) == 0 or key_points.xy[0] is None:
            return self.BASE_PITCH.copy()

        xy = key_points.xy[0]
        if xy.size == 0:
            return self.BASE_PITCH.copy()

        conf = (
            key_points.confidence[0].astype(np.float32)
            if (key_points.confidence is not None and len(key_points.confidence) > 0 and key_points.confidence[0] is not None)
            else np.ones((len(xy),), np.float32)
        )

        mask = conf > kp_thresh
        src_pts = xy[mask]
        dst_pts = np.array(CONFIG.vertices, dtype=np.float32)[mask]
        if src_pts.shape[0] < 4:
            return self.BASE_PITCH.copy()

        transformer = ViewTransformer(source=src_pts.astype(np.float32),
                                    target=dst_pts.astype(np.float32))

        player_dict  = tracks["players"][frame_idx]

        pitch_players = self.transform_positions(player_dict, transformer)
        if pitch_players.size == 0:
            return self.BASE_PITCH.copy()

        teams = np.array([info["team"] for info in player_dict.values()], dtype=int) if len(player_dict) else np.array([], int)
        team1_xy = pitch_players[teams == 0] if teams.size else np.empty((0, 2), np.float32)
        team2_xy = pitch_players[teams == 1] if teams.size else np.empty((0, 2), np.float32)

        # Use cached base pitch and optimized voronoi (with step)
        board = draw_pitch_voronoi_diagram_2(
            config=CONFIG,
            team_1_xy=team1_xy,
            team_2_xy=team2_xy,
            team_1_color=sv.Color.from_hex("00BFFF"),
            team_2_color=sv.Color.from_hex("FF1493"),
            opacity=0.5,
            padding=50,
            scale=0.1,
            pitch=self.BASE_PITCH.copy(),
            # if you added 'step' param to your improved function; otherwise remove it
            step=vor_step  # <-- comment out if your signature doesn't include it
        )
        return board


    def annotate_all_from_result(
        self,
        frame: np.ndarray,
        tracks: dict,
        frame_idx: int,
        CONFIG,
        result,
        kp_thresh: float = 0.5
    ):
        """Same as annotate_all, but uses a precomputed Ultralytics `result`."""
        canvas = frame.copy()

        # 1) keypoints once
        kps = sv.KeyPoints.from_ultralytics(result)

        # Defaults if no keypoints
        frame_annotated = canvas
        tactical_board = self.BASE_PITCH.copy()
        voronoi_board = self.BASE_PITCH.copy()

        if kps.xy is None or len(kps.xy) == 0 or kps.xy[0] is None or kps.xy[0].size == 0:
            return frame_annotated, tactical_board, voronoi_board

        xy = kps.xy[0]
        conf = (
            kps.confidence[0].astype(np.float32)
            if (kps.confidence is not None and len(kps.confidence) > 0 and kps.confidence[0] is not None)
            else np.ones((len(xy),), np.float32)
        )

        # 2) build correspondences & transformers
        mask = conf > kp_thresh
        src_img = xy[mask]                          # image-space
        dst_pitch = np.array(CONFIG.vertices)[mask] # pitch model-space

        have_H = src_img.shape[0] >= 4
        if have_H:
            T_i2p = ViewTransformer(source=src_img.astype(np.float32),
                                    target=dst_pitch.astype(np.float32))   # image -> pitch
            T_p2i = ViewTransformer(source=dst_pitch.astype(np.float32),
                                    target=src_img.astype(np.float32))     # pitch -> image
        else:
            T_i2p = T_p2i = None

        # 3) frame overlay (pitch->image)
        if T_p2i is not None:
            frame_all_points = T_p2i.transform_points(self.vertices.astype(np.float32))
            kp_all = sv.KeyPoints(xy=frame_all_points[np.newaxis, ...])
            frame_annotated = self.edge_annotator.annotate(scene=canvas, key_points=kp_all)
            frame_annotated = self.vertex_annotator.annotate(scene=frame_annotated, key_points=kp_all)

        # 4) transform tracks (image->pitch)
        def _tx(track_dict):
            if T_i2p is None or not track_dict:
                return np.empty((0, 2), np.float32)
            pts = np.array([info["position"] for info in track_dict.values()], dtype=np.float32)
            return T_i2p.transform_points(points=pts) if pts.size else np.empty((0, 2), np.float32)

        ball_dict    = tracks["ball"][frame_idx]
        player_dict  = tracks["players"][frame_idx]
        referee_dict = tracks["referees"][frame_idx]

        pitch_ball    = _tx(ball_dict)
        pitch_players = _tx(player_dict)
        pitch_refs    = _tx(referee_dict)

        # 5) tactical board
        tactical_board = draw_points_on_pitch(
            config=CONFIG,
            xy=pitch_ball,
            face_color=sv.Color.WHITE,
            edge_color=sv.Color.BLACK,
            radius=10,
            thickness=2,
            pitch=tactical_board,
        )

        player_colors = [info["team_color"] for info in player_dict.values()]
        seen = {}
        for idx, color in enumerate(player_colors):
            seen.setdefault(color, []).append(idx)
        for team_color, indices in seen.items():
            pts = pitch_players[indices] if pitch_players.size else np.empty((0, 2), np.float32)
            b, g, r = team_color
            col = sv.Color(r=r, g=g, b=b)
            tactical_board = draw_points_on_pitch(
                config=CONFIG,
                xy=pts,
                face_color=col,
                edge_color=sv.Color.BLACK,
                radius=16,
                thickness=2,
                pitch=tactical_board,          # <- keyword!
            )

        tactical_board = draw_points_on_pitch(
            config=CONFIG,
            xy=pitch_refs,
            face_color=sv.Color.from_hex("FFD700"),
            edge_color=sv.Color.BLACK,
            radius=16,
            thickness=2,
            pitch=tactical_board,          # <- keyword!
        )


        # 6) voronoi board (guard empty)
        teams = np.array([info["team"] for info in player_dict.values()], dtype=int) if len(player_dict) else np.array([], int)
        if pitch_players.size and teams.size:
            team1_xy = pitch_players[teams == 0]
            team2_xy = pitch_players[teams == 1]
            if not (team1_xy.size == 0 and team2_xy.size == 0):
                voronoi_board = draw_pitch_voronoi_diagram_2(
                    config=CONFIG,
                    team_1_xy=team1_xy,
                    team_2_xy=team2_xy,
                    team_1_color=sv.Color.from_hex("00BFFF"),
                    team_2_color=sv.Color.from_hex("FF1493"),
                    opacity=0.5,
                    padding=50,
                    scale=0.1,
                    pitch=None
                )

        return frame_annotated, tactical_board, voronoi_board
