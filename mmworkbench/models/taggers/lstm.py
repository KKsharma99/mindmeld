import numpy as np
import re

from ..helpers import extract_sequence_features
from .taggers import Tagger, get_tags_from_entities
from .bi_directional_lstm import LstmNetwork
from .embeddings import Embedding
from ..helpers import extract_sequence_features, get_label_encoder

DEFAULT_PADDED_TOKEN = '<UNK>'
DEFAULT_LABEL = 'O||O|'
DEFAULT_GAZ_LABEL = 'O'
DEFAULT_ENTITY_TOKEN_SPAN_INDEX = 2
GAZ_PATTERN_MATCH = 'in-gaz\|type:(\w+)\|pos:(\w+)\|'


class LSTMModel(Tagger):
    """"A LSTM model."""

    def __init__(self, config, resources):
        self.config = config
        self._resources = resources
        self.embedding = Embedding(self.config.params)
        self._tag_scheme = self.config.model_settings.get('tag_scheme', 'IOB').upper()
        self._label_encoder = get_label_encoder(self.config)

    def fit(self, examples, labels, resources=None):
        # Extract features and classes
        X, gaz = self._get_features(examples)
        embedding_matrix = self.embedding.get_encoding_matrix()
        embedding_gaz_matrix = self.embedding.get_gaz_encoding_matrix()

        all_tags = []
        for idx, label in enumerate(labels):
            all_tags.append(get_tags_from_entities(examples[idx], label, self._tag_scheme))

        encoded_labels = self.embedding.encode_labels(all_tags)
        labels_dict = self.embedding.label_encoding

        examples = np.asarray(X, dtype='int32')
        labels = np.asarray(encoded_labels, dtype='int32')
        seq_len = np.ones(len(examples)) * int(self.config.params['padding_length'])
        gaz = np.asarray(gaz, dtype='int32')

        self.config.params["seq_len"] = seq_len
        self.config.params["output_dimension"] = len(labels_dict.keys())
        self.config.params["embedding_matrix"] = embedding_matrix
        self.config.params["labels_dict"] = labels_dict
        self.config.params["embedding_gaz_matrix"] = embedding_gaz_matrix
        self.config.params["gaz_features"] = gaz

        self._clf = self._fit(examples, labels, self.config.params)
        return self

    def predict(self, examples):
        X, gaz = self._get_features(examples)
        embedding_matrix = self.embedding.get_encoding_matrix()
        embedding_gaz_matrix = self.embedding.get_gaz_encoding_matrix()

        examples = np.asarray(X, dtype='int32')
        gaz = np.asarray(gaz, dtype='int32')

        self.config.params["embedding_matrix"] = embedding_matrix
        self.config.params["embedding_gaz_matrix"] = embedding_gaz_matrix
        self.config.params["gaz_features"] = gaz

        self._clf.embedding_matrix = embedding_matrix
        self._clf.embedding_gaz_matrix = embedding_gaz_matrix
        self._clf.gaz_features = gaz

        tags_by_example = self._clf.predict(examples)

        prediction_wrapper = self._label_encoder.decode(tags_by_example, examples=examples)
        return prediction_wrapper

    def _get_model_constructor(self):
        """Returns the python class of the actual underlying model"""
        return LstmNetwork

    def _preprocess_query_data(self, list_of_gold_queries, padding_length):
        queries = []
        for label_query in list_of_gold_queries:
            padded_query = [DEFAULT_PADDED_TOKEN] * padding_length

            max_sequence_length = min(len(label_query.query.normalized_tokens), padding_length)
            for i in range(max_sequence_length):
                padded_query[i] = label_query.query.normalized_tokens[i]
            queries.append(padded_query)
        return queries

    def _get_features(self, examples):
        """Transforms a list of examples into a feature matrix.

        Args:
            examples (list of mmworkbench.core.Query): a list of queries
        Returns:
            (list of list of str): features in CRF suite format
        """
        x_feats = []
        gaz_feats = []
        for idx, example in enumerate(examples):
            x_feat, gaz_feat = self._extract_features(example)
            x_feats.append(x_feat)
            gaz_feats.append(gaz_feat)
        return x_feats, gaz_feats

    def _extract_features(self, example):
        """Extracts feature dicts for each token in an example.

        Args:
            example (mmworkbench.core.Query): an query
        Returns:
            (list dict): features
        """
        padding_length = self.config.params['padding_length']

        extracted_gaz_tokens = [DEFAULT_GAZ_LABEL] * padding_length
        extracted_sequence_features = extract_sequence_features(example,
                                                                self.config.example_type,
                                                                self.config.features,
                                                                self._resources)

        for index, extracted_gaz in enumerate(extracted_sequence_features):
            if len(extracted_gaz.keys()) > 0 and index < padding_length:
                combined_gaz_features = set()
                for key in extracted_gaz.keys():
                    regex_match = re.match(GAZ_PATTERN_MATCH, key)
                    if regex_match:
                        combined_gaz_features.add(regex_match.group(1))
                        # TODO: Found a lot of gaz features had both start and end
                        # for the positive info, so I removed that feature

                        # combined_gaz_features.add("{}-{}".format(
                        #     regex_match.group(1), regex_match.group(2)))

                if len(combined_gaz_features) == 0:
                    extracted_gaz_tokens[index] = DEFAULT_GAZ_LABEL
                else:
                    extracted_gaz_tokens[index] = ",".join(list(combined_gaz_features))

        padded_query = [DEFAULT_PADDED_TOKEN] * padding_length
        max_sequence_length = min(len(example.normalized_tokens), padding_length)
        for i in range(max_sequence_length):
            padded_query[i] = example.normalized_tokens[i]

        encoded_gaz = self.embedding.transform_gaz_query(extracted_gaz_tokens)
        padded_query = self.embedding.transform_example(padded_query)

        return padded_query, encoded_gaz

    def _preprocess_data(self, X):
        """Converts data into formats of CRF suite.

        Args:
            X (list of dict): features of an example
        Returns:
            (list of list of str): features in CRF suite format
        """
        new_X = []
        for feat_seq in X:
            feat_list = []
            for feature in feat_seq:
                temp_list = []
                for elem in sorted(feature.keys()):
                    temp_list.append(elem + '=' + str(feature[elem]))
                feat_list.append(temp_list)
            new_X.append(feat_list)
        return new_X

    def _fit(self, X, y, params):
        """Trains a classifier without cross-validation.

        Args:
            X (list of list of list of str): a list of queries to train on
            y (list of list of str): a list of expected labels
            params (dict): Parameters of the classifier
        """
        model_class = self._get_model_constructor()
        return model_class(**params).fit(X, y)