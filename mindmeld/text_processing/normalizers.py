# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 Cisco Systems, Inc. and others.  All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module contains Normalizers."""

from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class Normalizer(ABC):
    """Abstract Normalizer Base Class."""

    def __init__(self):
        """Creates a Normalizer instance."""
        pass

    @abstractmethod
    def normalize(self, text):
        """
        Args:
            text (str): Input text.
        Returns:
            normalized_text (str): Normalized Text.
        """
        raise NotImplementedError("Subclasses must implement this method")


class NoOpNormalizer(Normalizer):
    """A No-Ops Normalizer."""

    def __init__(self):
        pass

    def normalize(self, text):
        """
        Args:
            text (str): Input text.
        Returns:
            normalized_text (str): Returns the original text.
        """
        return " N NoOp " + text


# TODO: Implement
class RegexNormalizer(Normalizer):
    """A Regex Normalizer."""

    def __init__(self):
        pass

    def normalize(self, text):
        """
        Args:
            text (str): Input text.
        Returns:
            normalized_text (str): Normalized Text.
        """
        return " regex " + text


# TODO: Implement
class UnicodeCharacterNormalizer(Normalizer):
    """A No-Ops Normalizer."""

    def __init__(self):
        pass

    def normalize(self, text):
        """
        Args:
            text (str): Input text.
        Returns:
            normalized_text (str): Normalized Text.
        """
        return " unicodeChar " + text


class NormalizerFactory:
    """Normalizer Factory Class"""

    @staticmethod
    def get_normalizer(normalizer):
        """A static method to get a Normalizer

        Args:
            normalizer (str): Name of the desired Normalizer class
        Returns:
            (Normalizer): Normalizer Class
        """
        if normalizer == NoOpNormalizer.__name__:
            return NoOpNormalizer()
        elif normalizer == RegexNormalizer.__name__:
            return RegexNormalizer()
        elif normalizer == UnicodeCharacterNormalizer.__name__:
            return UnicodeCharacterNormalizer()
        raise AssertionError(f" {normalizer} is not a valid Normalizer.")


# TODO: Consider how to create a custom Normalizer based on an allowed intents pattern a
# user provides.
