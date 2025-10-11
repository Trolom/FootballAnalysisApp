from typing import Generator, Iterable, List, TypeVar

import numpy as np
import supervision as sv
import torch

import umap

from sklearn.cluster import KMeans
from tqdm import tqdm
from transformers import AutoProcessor, SiglipVisionModel
from transformers import CLIPProcessor, CLIPModel

V = TypeVar("V")

SIGLIP_MODEL_PATH = 'google/siglip-base-patch16-224'


def create_batches(
    sequence: Iterable[V], batch_size: int
) -> Generator[List[V], None, None]:
    """
    Generate batches from a sequence with a specified batch size.
    """
    batch_size = max(batch_size, 1)
    current_batch = []
    for element in sequence:
        if len(current_batch) == batch_size:
            yield current_batch
            current_batch = []
        current_batch.append(element)
    if current_batch:
        yield current_batch


class TeamClassifier:
    """
    A classifier that uses a pre-trained SiglipVisionModel for feature extraction,
    UMAP for dimensionality reduction, and KMeans for clustering.
    """
    def __init__(self, device: str = 'cpu', batch_size: int = 32):
        """
       Initialize the TeamClassifier with device and batch size.

       Args:
           device (str): The device to run the model on ('cpu' or 'cuda').
           batch_size (int): The batch size for processing images.
       """
        self.device = device
        self.batch_size = batch_size
        #self.features_model = SiglipVisionModel.from_pretrained(SIGLIP_MODEL_PATH).to(device)
        #self.processor = AutoProcessor.from_pretrained(SIGLIP_MODEL_PATH, use_fast=True)
        self.features_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32", use_fast=True)
        self.reducer = umap.UMAP(n_components=3)
        self.cluster_model = KMeans(n_clusters=2)


    def extract_features(self, crops: List[np.ndarray]) -> np.ndarray:
        """
        Extract image features using CLIP fast image processor.
        Returns: (N, D) numpy array of embeddings.
        """
        if not crops:
            return np.empty((0, 512), dtype=np.float32)  # 512 for ViT-B/32

        # Ensure PIL images (fast processor accepts PIL/np)
        crops_pil = [sv.cv2_to_pillow(c) for c in crops]

        data = []
        with torch.no_grad():
            for batch in tqdm(create_batches(crops_pil, self.batch_size), desc="Embedding extraction"):
                # Fast image preprocessing
                pixel_values = self.processor(images=batch, return_tensors="pt").pixel_values.to(self.device)

                # Get image embeddings directly (no text needed)
                feats = self.features_model.get_image_features(pixel_values=pixel_values)

                data.append(feats.cpu().numpy())

        return np.concatenate(data, axis=0)


    def fit(self, crops: List[np.ndarray]) -> None:
        """
        Fit the classifier model on a list of image crops.
        """
        data = self.extract_features(crops)
        projections = self.reducer.fit_transform(data)
        self.cluster_model.fit(projections)


    def predict(self, crops: List[np.ndarray]) -> np.ndarray:
        """
        Predict the cluster labels for a list of image crops.
        Returns: np.ndarray: Predicted cluster labels.
        """
        if len(crops) == 0:
            return np.array([])

        data = self.extract_features(crops)
        projections = self.reducer.transform(data)
        return self.cluster_model.predict(projections)