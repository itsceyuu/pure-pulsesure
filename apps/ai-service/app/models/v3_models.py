"""Compact V3 waveform and time-frequency quality models."""

from __future__ import annotations

import torch
from torch import nn


class ResidualBlock1D(nn.Module):
    def __init__(self, input_channels: int, output_channels: int, stride: int = 1) -> None:
        super().__init__()
        self.main = nn.Sequential(
            nn.Conv1d(input_channels, output_channels, kernel_size=5, stride=stride, padding=2, bias=False),
            nn.BatchNorm1d(output_channels),
            nn.ReLU(inplace=True),
            nn.Dropout(0.10),
            nn.Conv1d(output_channels, output_channels, kernel_size=5, padding=2, bias=False),
            nn.BatchNorm1d(output_channels),
        )
        self.skip = (
            nn.Identity()
            if input_channels == output_channels and stride == 1
            else nn.Sequential(
                nn.Conv1d(input_channels, output_channels, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm1d(output_channels),
            )
        )
        self.activation = nn.ReLU(inplace=True)

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.activation(self.main(inputs) + self.skip(inputs))


class CompactPPGQualityCNN(nn.Module):
    """Small no-SE residual model for PPG, FDP, and SDP input channels."""

    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv1d(3, 16, kernel_size=7, padding=3, bias=False),
            nn.BatchNorm1d(16),
            nn.ReLU(inplace=True),
            ResidualBlock1D(16, 16),
            ResidualBlock1D(16, 32, stride=2),
            ResidualBlock1D(32, 64, stride=2),
        )
        self.average_pool = nn.AdaptiveAvgPool1d(1)
        self.maximum_pool = nn.AdaptiveMaxPool1d(1)
        self.classifier = nn.Sequential(nn.Flatten(), nn.Dropout(0.20), nn.Linear(128, 1))

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        encoded = self.encoder(inputs)
        pooled = torch.cat([self.average_pool(encoded), self.maximum_pool(encoded)], dim=1)
        return self.classifier(pooled).squeeze(1)


class CompactSTFTQualityCNN(nn.Module):
    """Small 2-D CNN for standardized log-power STFT tensors."""

    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = nn.Sequential(nn.Flatten(), nn.Dropout(0.25), nn.Linear(64, 1))

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.encoder(inputs)).squeeze(1)


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
