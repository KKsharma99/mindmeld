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
from abc import ABC, abstractmethod
import re
import logging
import spacy

from .resource_loader import ResourceLoader
from .components._config import get_auto_annotator_config
from .system_entity_recognizer import DucklingRecognizer
from .markup import load_query, load_query_file, dump_queries
from .core import Entity, Span, QueryEntity
from .query_factory import QueryFactory

logger = logging.getLogger(__name__)

class Annotator(ABC):
    """
    Abstract Annotator class that can be used to build a custom Annotation class.
    """
    
    def __init__(self, app_path, config=None, resource_loader=None):
        """ Initializes an annotator."""
        self.app_path = app_path
        self.config = get_auto_annotator_config(app_path=app_path,config=config)
        self._resource_loader = (
            resource_loader or ResourceLoader.create_resource_loader(app_path)
        )
        self.annotate_file_entities_map = self._get_file_entities_map(action="annotate")

    def _get_file_entities_map(self, action="annotate"):
        """ Creates a dictionary that maps file paths to entities given
        regex rules defined in the config.

        Args:
            action (str): Can be "annotate" or "unannotate". Used as a key
                to access a list of regex rules in the config dictionary.
        
        Returns:
            file_entities_map (dict): A dictionary that maps file paths in an
                App to a list of entities.
        """
        all_file_paths = self._resource_loader.get_all_file_paths()
        file_entities_map = {path:[] for path in all_file_paths}
        rules = self.config[action]
        for rule in rules:
            pattern = self._get_pattern(rule) 
            filtered_paths = self._resource_loader.filter_file_paths(
                file_pattern=pattern, file_paths=all_file_paths 
            )
            for path in filtered_paths:
                entities = self._get_entities(rule)
                file_entities_map[path] = entities
        return file_entities_map

    def _get_pattern(self, rule):
        """ Extract the portion of a regex rule that refers to file paths.

        Args:
            rule (str): Regex rule specifying allowed file paths and entities.
        
        Returns:
            pattern (str): Regex pattern specifying allowed file paths.
        """
        pattern = "/".join(rule.split("/")[:-1]) 
        pattern = pattern.replace(".*", ".+")
        pattern = pattern.replace("*", ".+")
        prefix = ".*" if pattern[0] == "/" else ".*/"
        return prefix + pattern

    def _get_entities(self, rule):
        """ Extract the portion of a regex rule that refers to file paths.
        
        Args:
            rule (str): Regex rule specifying allowed file paths and entities.
        
        Returns:
            valid_entities (list): List of valid entities specified in the rule.
        """
        entities = rule.split("/")[-1]
        entities = re.sub('[()]',"", entities).split("|")
        valid_entities = []
        for entity in entities:
            if entity=="*" or self.valid_entity_check(entity):
                valid_entities.append(entity)
            else:
                logger.warning("%s is not a valid entity. Skipping entity.", entity)
        return valid_entities

    @abstractmethod
    def valid_entity_check(self, entity):
        """ Determine if an entity type is valid.

        Args:
            entity (str): Name of entity to annotate.
        
        Returns:
            bool: Whether entity is valid.
        """
        return True

    def annotate(self):
        """ Annotate data based on configurations in the config.py file.
        """
        file_entities_map = self.annotate_file_entities_map
        self._modify_queries(file_entities_map, action="annotate")

    def unannotate(self):
        """ Unannotate data based on configurations in the config.py file.
        """
        if not self.config["unannotate"]:
            logger.warning("Unnanotate is set to None in the config.")
            return
        file_entities_map = self._get_file_entities_map(action="unannotate")
        self._modify_queries(file_entities_map, action="unannotate")

    def _modify_queries(self, file_entities_map, action):
        """ Iterates through App files and annotates or unannotates queries.

        Args:
            file_entities_map (dict): A dictionary that maps a file paths
                in an App to a list of entities.
        """
        query_factory = QueryFactory.create_query_factory(self.app_path)
        for path in file_entities_map:
            processed_queries = self._get_processed_queries(
                file_path=path, query_factory=query_factory
            )
            for processed_query in processed_queries:
                entity_types = file_entities_map[path]
                if action == "annotate":
                    self._annotate_query(
                        processed_query=processed_query, entity_types=entity_types
                    )
                elif action == "unannotate":
                    self._unannotate_query(
                        processed_query=processed_query, entity_types=entity_types
                    )
            annotated_queries = [query for query in dump_queries(processed_queries)]
            with open(path, "w") as outfile:
                outfile.write("".join(annotated_queries))
                outfile.close()

    def _get_processed_queries(self, file_path, query_factory):
        """ Converts queries in a given path to processed queries.
        Skips and presents a warning if loading the query creates an error.

        Args:
            file_path (str): Path to file containing queries.
            query_factory (QueryFactory): Used to generate processed queries.
        
        Returns:
            processed_queries (list): List of processed queries from file.
        """
        with open(file_path) as infile:
            queries = infile.readlines()
        processed_queries = []
        for query in queries:
            try:
                processed_query = load_query(
                    markup=query, query_factory=query_factory
                )
                processed_queries.append(processed_query)
            except:
                logger.warning(
                    "Skipping query. Error in processing: " + query
                )
        return processed_queries

    def _annotate_query(self, processed_query, entity_types):
        """ Updates the entities of a processed query with newly
        annotated entities.

        Args:
            processed_query (ProcessedQuery): The processed query to update.
            entity_types (list): List of entities allowed for annotation.
        """
        current_entities = list(processed_query.entities)
        annotated_entities = self._get_annotated_entities(
            processed_query=processed_query, entity_types=entity_types
        )
        final_entities = self._resolve_conflicts(
            current_entities=current_entities, annotated_entities=annotated_entities
        )
        processed_query.entities = tuple(final_entities)

    def _get_annotated_entities(self, processed_query, entity_types=None):
        """ Creates a list of query entities after parsing the text of a
        processed query.

        Args:
            processed_query (ProcessedQuery): A processed query.
            entity_types (list): List of entities allowed for annotation.
        
        Returns:
            query_entities (list): List of query entities.
        """
        if len(entity_types) == 0:
            return []
        entity_types = None if entity_types == ["*"] else entity_types
        items = self.parse(
            sentence = processed_query.query.text, entity_types=entity_types
        )
        query_entities = [self._item_to_query_entity(item, processed_query) for item in items]
        return query_entities if len(query_entities) > 0 else []

    def _item_to_query_entity(self, item, processed_query):
        """ Converts an item returned from parse into a query entity.

        Args:
            item (dict): Dictionary representing an entity with the keys -
                "body", "start", "end", "value", "dim".
            processed_query (ProcessedQuery): The processed query that the
                entity is found in.

        Returns:
            query_entity (QueryEntity): The converted query entity.
        """
        span = Span(
            start=item["start"], end=item["end"] - 1
        )
        entity = Entity(
            text=item["body"], entity_type=item["dim"], value=item["value"]
        )
        query_entity = QueryEntity.from_query(
            query=processed_query.query, span=span, entity=entity
        )
        return query_entity

    def _resolve_conflicts(self, current_entities, annotated_entities):
        """ Resolve overlaps between existing entities and newly annotad entities.

        Args:
            current_entities (list): List of existing query entities.
            annotated_entities (list): List of new query entities.
        
        Returns:
            final_entities (list): List of resolved query entities.
        """
        overwrite = self.config["overwrite"]
        base_entities = annotated_entities if overwrite else current_entities
        other_entities = current_entities if overwrite else annotated_entities

        additional_entities = []
        for o_entity in other_entities:
            no_overlaps = [
                self._no_overlap(o_entity, b_entity) for b_entity in base_entities
            ]
            if all(no_overlaps):
                additional_entities.append(o_entity)
        return base_entities + additional_entities

    def _no_overlap(self, entity_one, entity_two):
        """ Returns True if two query entities do not overlap.
        """
        return (
            entity_one.span.start > entity_two.span.end or
            entity_two.span.start > entity_one.span.end
        )

    def _unannotate_query(self, processed_query, entity_types):
        """ Removes specified entities in a processed query.

        Args:
            processed_query (ProcessedQuery): A processed query.
            entity_types (list): List of entities to remove.
        """
        if entity_types == ["*"]:
            processed_query.entities = ()
        final_entities = []
        for query_entity in processed_query.entities:
            if query_entity.entity.type not in entity_types:
                final_entities.append(query_entity)
        processed_query.entities = tuple(final_entities)

    @abstractmethod
    def parse(self, sentence, **kwargs):
        """ Extract entities from a sentence. Detected entities should be
        represented as dictionaries with the following keys: "body", "start"
        (start index), "end" (end index), "value", "dim" (entity type). 
        
        Args:
            sentence (str): Sentence to detect entities.
        
        Returns:
            entities (list): List of entity dictionaries.

        """
        raise NotImplementedError("Subclasses must implement this method")

class SpacyAnnotator(Annotator):
    """ Annotator class that uses spacy to generate annotations.
    """
    def __init__(self, app_path, config=None, model="en_core_web_lg", **kwargs):
        super().__init__(app_path=app_path, config=config, **kwargs)
        logger.info("Loading spacy model %s.", model)
        self.nlp = spacy.load(model)
        self.model = model
        self.duckling = DucklingRecognizer.get_instance()
        self.SYS_MAPPINGS = {
                        "money": "sys_amount-of-money",
                        "cardinal": "sys_number",
                        "ordinal": "sys_ordinal",
                        "person": "sys_person",
                        "percent": "sys_percent",
                        "distance": "sys_distance",
                        "quantity": "sys_weight"
                    }
    
    def valid_entity_check(self, entity):
        entity = entity.lower().strip()
        valid_entities = [
            "sys_time", "sys_interval", "sys_duration", "sys_number", "sys_amount-of-money",
            "sys_distance", "sys_weight", "sys_ordinal", "sys_quantity", "sys_percent",
            "sys_org", "sys_loc", "sys_person", "sys_gpe", "sys_norp", "sys_fac", "sys_product",
            "sys_event", "sys_law", "sys_langauge", "sys_work_of_art","sys_other_quantity"]
        return True if entity in valid_entities else False

    def parse(
        self,
        sentence,
        entity_types=None
    ):
        doc = self.nlp(sentence)
        spacy_entities = [
            {
                "body": ent.text,
                "start": ent.start_char,
                "end": ent.end_char,
                "value": {"value": ent.text},
                "dim": ent.label_.lower(),
            }
            for ent in doc.ents
        ]
        
        entities = []
        for entity in spacy_entities:
            if entity["dim"] in ["time", "date"]:
                entity = self._resolve_time_date(entity, entity_types)
            elif entity["dim"] == "cardinal":
                entity = self._resolve_cardinal(entity)
            elif entity["dim"] == "money":
                entity = self._resolve_money(entity)
            elif entity["dim"] == "ordinal":
                entity = self._resolve_ordinal(entity)
            elif entity["dim"] == "quantity":
                entity = self._resolve_quantity(entity)
            elif entity["dim"] == "percent":
                entity = self._resolve_percent(entity)
            elif entity["dim"] == "person":
                entity = self._resolve_person(entity)
            else:
                entity["dim"] = "sys_" + entity["dim"]
            
            if entity:
                entities.append(entity)

        if entity_types:
            entities = [e for e in entities if e["dim"] in entity_types]
        
        return entities

    def _resolve_time_date(self, entity, entity_types=None):
        """ Heuristic is to assign value if there is an exact body match. Order of priority
        is duration, interval, time."""
        candidates = self.duckling.get_candidates_for_text(entity["body"])

        if len(candidates) == 0:
            return
        
        time_entities = ["sys_duration", "sys_interval", "sys_time"]
        if entity_types:
            time_entities = [e for e in time_entities if e in entity_types]
        
        if self._resolve_time_exact_match(entity, candidates, time_entities):
            return entity
        elif self._resolve_time_largest_substring(entity, candidates, time_entities):
            return entity
        
    def _get_time_entity_type(self, candidate):
        if candidate["dim"] == "duration":
            return "sys_duration"
        if candidate["dim"] == "time":
            if candidate["value"]["type"] == "interval":
                return "sys_interval"
            else:
                return "sys_time"
            
    def _resolve_time_exact_match(self, entity, candidates, time_entities):
        for candidate in candidates:
            candidate_entity = self._get_time_entity_type(candidate)
            if ( 
                candidate_entity in time_entities and
                candidate["body"] == entity["body"]
            ):
                entity["dim"] = candidate_entity
                entity["value"] = candidate["value"]
                return entity
    
    def _resolve_time_largest_substring(self, entity, candidates, time_entities):
        for time_entity in time_entities:
            largest_candidate = None
            for candidate in candidates:
                candidate_entity = self._get_time_entity_type(candidate)
                if ( 
                    candidate_entity == time_entity and
                    candidate["body"] in entity["body"] and
                    (
                        not largest_candidate or
                        len(candidate["body"]) > len(largest_candidate["body"])
                    )                                                                   
                ):
                    largest_candidate = candidate
            if largest_candidate:
                entity["body"] = largest_candidate["body"]
                offset = entity["start"]
                entity["start"] = offset + largest_candidate["start"]
                entity["end"] = offset + largest_candidate["end"]
                entity["value"] = largest_candidate["value"]
                entity["dim"] = time_entity
                return entity
            
    def _resolve_cardinal(self, entity):
        return self._resolve_exact_match(entity)
    
    def _resolve_money(self, entity):
        # TODO: Check if a '$' is infront of the token
        return self._resolve_exact_match(entity)
        
    def _resolve_ordinal(self, entity):
        return self._resolve_exact_match(entity)
            
    def _resolve_exact_match(self, entity):
        entity["dim"] = self.SYS_MAPPINGS[entity["dim"]]
        
        candidates = self.duckling.get_candidates_for_text(entity["body"])
        if len(candidates) == 0:
            return
        
        for candidate in candidates:
            if (
                candidate["entity_type"] == entity["dim"]
                and entity["body"] == candidate["body"]
            ):
                    entity["value"] = candidate["value"]
                    return entity

    def _resolve_quantity(self, entity):
        candidates = self.duckling.get_candidates_for_text(entity["body"])
        if len(candidates) == 0:
            entity["dim"] = "sys_other_quantity"
            return entity

        for entity_type in ["distance", "quantity"]:
            for candidate in candidates:
                if (
                    candidate["dim"] == entity_type and
                    candidate["body"] == entity["body"]
                ):
                    entity["value"] = candidate["value"]
                    entity["dim"] = self.SYS_MAPPINGS[entity_type]
                    return entity

        if self._resolve_quantity_largest_substring(entity, candidates):
            return entity
        else:
            entity["dim"] = "sys_other_quantity"
            return entity

    def _resolve_quantity_largest_substring(self, entity, candidates):
        for entity_type in ["distance", "quantity"]:
            largest_candidate = None
            for candidate in candidates:
                candidate_entity = candidate["dim"]
                if ( 
                    candidate_entity == entity_type and
                    candidate["body"] in entity["body"] and
                    (
                        not largest_candidate or
                        len(candidate["body"]) > len(largest_candidate["body"])
                    )                                                                   
                ):
                    largest_candidate = candidate
            if largest_candidate:
                entity["body"] = largest_candidate["body"]
                offset = entity["start"]
                entity["start"] = offset + largest_candidate["start"]
                entity["end"] = offset + largest_candidate["end"]
                entity["value"] = largest_candidate["value"]
                entity["dim"] = entity_type
                return entity
    
    def _resolve_percent(self, entity):
        entity["dim"] = self.SYS_MAPPINGS[entity["dim"]]
        
        candidates = self.duckling.get_candidates_for_text(entity["body"])
        if len(candidates) == 0:
            return

        possible_values = []
        for candidate in candidates:
            if candidate["entity_type"] == "sys_number":
                possible_values.append(candidate["value"]["value"])
        entity['value']['value'] = max(possible_values)/100
        return entity

    
    def _resolve_person(self, entity):
        entity["dim"] = self.SYS_MAPPINGS[entity["dim"]]
        
        if len(entity["body"]) >= 2 and entity["body"][-2:] == "'s":
            entity["value"] = entity["body"][:-2]
            entity["body"] = entity["body"][:-2]
            entity["end"] -= 2
        return entity