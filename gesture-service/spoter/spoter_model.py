"""
SPOTER (Sign Pose-based Transformer) architecture for word-level sign language recognition.
Adapted from: https://github.com/maty-bohacek/spoter
Reference: Boháček & Hrúz, "Sign Pose-based Transformer for Word-level Sign Language Recognition", WACV 2022.
"""

import copy
from typing import Optional
import torch
import torch.nn as nn


def _get_clones(mod, n):
    return nn.ModuleList([copy.deepcopy(mod) for _ in range(n)])


class SPOTERTransformerDecoderLayer(nn.TransformerDecoderLayer):
    """
    Custom TransformerDecoderLayer that deactivates self-attention,
    keeping only cross-attention (class query attending to landmark sequence memory) and FFN.
    """

    def __init__(self, d_model: int, nhead: int, dim_feedforward: int = 2048,
                 dropout: float = 0.1, activation: str = "relu"):
        super().__init__(d_model, nhead, dim_feedforward, dropout, activation)
        # Retain self.self_attn attribute for PyTorch 2.x TransformerDecoder metadata checks,
        # but omit invoking it in forward() to deactivate self-attention as required by SPOTER.

    def forward(
        self,
        tgt: torch.Tensor,
        memory: torch.Tensor,
        tgt_mask: Optional[torch.Tensor] = None,
        memory_mask: Optional[torch.Tensor] = None,
        tgt_key_padding_mask: Optional[torch.Tensor] = None,
        memory_key_padding_mask: Optional[torch.Tensor] = None,
        tgt_is_causal: bool = False,
        memory_is_causal: bool = False,
    ) -> torch.Tensor:
        # Cross-attention without self-attention
        tgt = tgt + self.dropout1(tgt)
        tgt = self.norm1(tgt)
        tgt2 = self.multihead_attn(
            tgt, memory, memory,
            attn_mask=memory_mask,
            key_padding_mask=memory_key_padding_mask
        )[0]
        tgt = tgt + self.dropout2(tgt2)
        tgt = self.norm2(tgt)
        tgt2 = self.linear2(self.dropout(self.activation(self.linear1(tgt))))
        tgt = tgt + self.dropout3(tgt2)
        tgt = self.norm3(tgt)
        return tgt


class SPOTER(nn.Module):
    """
    SPOTER architecture:
    - Input: Sequence of skeletal landmarks (T frames, hidden_dim=108 coordinates)
    - 6 encoder layers, 6 modified decoder layers
    - Class query token decoded into sign class logits
    """

    def __init__(
        self,
        num_classes: int,
        hidden_dim: int = 108,
        nhead: int = 9,
        num_encoder_layers: int = 6,
        num_decoder_layers: int = 6,
        dim_feedforward: int = 2048,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.num_classes = num_classes
        self.hidden_dim = hidden_dim

        # Positional parameter
        self.row_embed = nn.Parameter(torch.rand(50, hidden_dim))
        self.pos = nn.Parameter(
            torch.cat([self.row_embed[0].unsqueeze(0).repeat(1, 1, 1)], dim=-1)
            .flatten(0, 1)
            .unsqueeze(0)
        )
        self.class_query = nn.Parameter(torch.rand(1, hidden_dim))
        self.transformer = nn.Transformer(
            d_model=hidden_dim,
            nhead=nhead,
            num_encoder_layers=num_encoder_layers,
            num_decoder_layers=num_decoder_layers,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
        )
        self.linear_class = nn.Linear(hidden_dim, num_classes)

        # Replace standard decoder layers with SPOTER decoder layers
        custom_decoder_layer = SPOTERTransformerDecoderLayer(
            d_model=self.transformer.d_model,
            nhead=self.transformer.nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            activation="relu",
        )
        self.transformer.decoder.layers = _get_clones(
            custom_decoder_layer, self.transformer.decoder.num_layers
        )

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.
        Args:
            inputs: Tensor of shape (T, 108) or (B, T, 108)
        Returns:
            Logits of shape (1, 1, num_classes) if single sequence, or (B, 1, num_classes) if batched.
        """
        if inputs.dim() == 2:
            # Single sample: (T, hidden_dim)
            h = torch.unsqueeze(inputs.flatten(start_dim=1), 1).float()  # (T, 1, hidden_dim)
            h = self.transformer(
                self.pos + h,
                self.class_query.unsqueeze(0)  # (1, 1, hidden_dim)
            ).transpose(0, 1)  # (1, 1, hidden_dim)
            res = self.linear_class(h)  # (1, 1, num_classes)
            return res
        elif inputs.dim() == 3:
            # Batched: (B, T, hidden_dim)
            b = inputs.size(0)
            h = inputs.transpose(0, 1).float()  # (T, B, hidden_dim)
            query = self.class_query.unsqueeze(1).expand(-1, b, -1)  # (1, B, hidden_dim)
            h = self.transformer(self.pos + h, query).transpose(0, 1)  # (B, 1, hidden_dim)
            res = self.linear_class(h)  # (B, 1, num_classes)
            return res
        else:
            raise ValueError(f"Expected 2D or 3D tensor, got shape {inputs.shape}")

    @classmethod
    def from_checkpoint(cls, checkpoint: dict, device: torch.device | None = None) -> "SPOTER":
        """Instantiate and load a SPOTER model dynamically from a saved checkpoint dictionary."""
        num_classes = checkpoint["num_classes"]
        hidden_dim = checkpoint.get("hidden_dim", 108)
        nhead = checkpoint.get("nhead", 9)
        state_dict = checkpoint["model_state_dict"]

        num_enc = checkpoint.get("num_encoder_layers")
        if num_enc is None:
            enc_keys = [k for k in state_dict if k.startswith("transformer.encoder.layers.") and k.endswith(".norm1.weight")]
            num_enc = len(enc_keys) if enc_keys else 6

        num_dec = checkpoint.get("num_decoder_layers")
        if num_dec is None:
            dec_keys = [k for k in state_dict if k.startswith("transformer.decoder.layers.") and k.endswith(".norm1.weight")]
            num_dec = len(dec_keys) if dec_keys else 6

        model = cls(
            num_classes=num_classes,
            hidden_dim=hidden_dim,
            nhead=nhead,
            num_encoder_layers=num_enc,
            num_decoder_layers=num_dec,
        )
        model.load_state_dict(state_dict)
        if device is not None:
            model.to(device)
        model.eval()
        return model

