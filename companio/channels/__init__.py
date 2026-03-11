"""Chat channels module with plugin architecture."""

from companio.channels.base import BaseChannel
from companio.channels.manager import ChannelManager

__all__ = ["BaseChannel", "ChannelManager"]
