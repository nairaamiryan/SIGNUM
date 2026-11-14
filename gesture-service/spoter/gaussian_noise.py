import torch


class GaussianNoise(object):
    """
    Data augmentation that adds zero-mean Gaussian noise to landmark coordinate tensors.
    As described in the SPOTER paper: N(0, 0.001) is added during training.
    """

    def __init__(self, mean: float = 0.0, std: float = 0.001):
        self.mean = mean
        self.std = std

    def __call__(self, tensor: torch.Tensor) -> torch.Tensor:
        return tensor + torch.randn(tensor.size(), dtype=tensor.dtype, device=tensor.device) * self.std + self.mean

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(mean={self.mean}, std={self.std})"
