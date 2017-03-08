# coding=utf-8
"""
This module contains the domain classifier component.
"""

from __future__ import unicode_literals
from builtins import object

import copy
import logging
import os

from sklearn.externals import joblib

from ..exceptions import ClassifierLoadError, FileNotFoundError
from ..core import Query

from ..models import ModelConfig
from ..models.helpers import create_model

logger = logging.getLogger(__name__)


class Classifier(object):
    DEFAULT_CONFIG = None

    def __init__(self, resource_loader):
        """Initializes a classifier

        Args:
            resource_loader (ResourceLoader): An object which can load resources for the classifier
        """
        self._resource_loader = resource_loader
        self._model = None  # will be set when model is fit or loaded

    def fit(self, model_type=None, features=None, params_grid=None, cv=None, queries=None):
        """Trains the model

        Args:
            model_type (str): The type of model to use. If omitted, the default model type will
                be used.
            features (dict): If omitted, the default features for the model type will be used.
            params_grid (dict): If omitted the default params will be used
            cv (None, optional): Description
            queries (list of ProcessedQuery): The labeled queries to use as training data

        """
        raise NotImplementedError('Subclasses must implement this method')

    def predict(self, query):
        """Predicts a domain for the specified query

        Args:
            query (Query): The input query

        Returns:
            str: the predicted domain
        """
        raise NotImplementedError('Subclasses must implement this method')

    def predict_proba(self, query):
        """Generates multiple hypotheses and returns their associated probabilities

        Args:
            query (Query): The input query

        Returns:
            list: a list of tuples of the form (str, float) grouping predictions and their
                probabilities
        """
        raise NotImplementedError('Subclasses must implement this method')

    def evaluate(self, use_blind=False):
        """Evaluates the model on the specified data

        Returns:
            TYPE: Description
        """
        raise NotImplementedError('Subclasses must implement this method')

    def get_model_config(self, config_name, **kwargs):
        config_name = config_name or self.DEFAULT_CONFIG['default_model']
        model_config = copy.copy(self.DEFAULT_CONFIG['models'][config_name])
        model_config.update(kwargs)
        return ModelConfig(**model_config)

    def dump(self, model_path):
        """Persists the model to disk.

        Args:
            model_path (str): The location on disk where the model should be stored

        """
        # make directory if necessary
        folder = os.path.dirname(model_path)
        if not os.path.isdir(folder):
            os.makedirs(folder)

        joblib.dump(self._model, model_path)

    def load(self, model_path):
        """Loads the model from disk

        Args:
            model_path (str): The location on disk where the model is stored

        """
        try:
            self._model = joblib.load(model_path)
        except FileNotFoundError:
            msg = 'Unable to load {}. Pickle file not found at {!r}'
            raise ClassifierLoadError(msg.format(self.__class__.__name__, model_path))

    def _get_queries_and_labels(self, queries=None):
        """Returns the set of queries and their classes to train on

        Args:
            queries (list): A list of ProcessedQuery objects to train. If not passed, the default
                training set will be loaded.

        """
        raise NotImplementedError('Subclasses must implement this method')


class StandardClassifier(Classifier):
    """The Standard classifier is a generic base for classification of strings.

    Attributes:
        DEFAULT_CONFIG (dict): The default configuration
        MODEL_CLASS (type): The the class of the underlying model.
    """

    def fit(self, queries=None, config_name=None, **kwargs):
        """Trains the model

        Args:
            queries (list of ProcessedQuery): The labeled queries to use as training data
            config_name (str): The type of model to use. If omitted, the default model type will
                be used.

        """
        queries, classes = self._get_queries_and_labels(queries)
        config = self.get_model_config(config_name, **kwargs)
        model = create_model(config)
        gazetteers = self._resource_loader.get_gazetteers()
        model.register_resources(gazetteers=gazetteers)
        model.fit(queries, classes)
        self._model = model

    def predict(self, query):
        """Predicts a domain for the specified query

        Args:
            query (Query): The input query

        Returns:
            str: the predicted domain
        """
        if not isinstance(query, Query):
            query = self._resource_loader.query_factory.create_query(query)
        return self._model.predict([query])[0]

    def predict_proba(self, query):
        """Generates multiple hypotheses and returns their associated probabilities

        Args:
            query (Query): The input query

        Returns:
            list: a list of tuples of the form (str, float) grouping predictions and their
                probabilities
        """
        return self._model.predict_proba([query])[0]

    def evaluate(self, use_blind=False):
        """Evaluates the model on the specified data

        Returns:
            TYPE: Description
        """
        raise NotImplementedError('Still need to implement this. Sorry!')

    def load(self, model_path):
        super().load(model_path)
        if self._model:
            gazetteers = self._resource_loader.get_gazetteers()
            self._model.register_resources(gazetteers=gazetteers)
