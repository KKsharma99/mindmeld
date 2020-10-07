Working with the Auto Annotator
=====================================================

The Auto Annotator

  - is a tool to automatically annotate or unannotate select entities across all labelled data in an application.
  - supports the development of custom Annotators.

.. note::

   The examples in this section require the :doc:`HR Assistant <../blueprints/hr_assistant>` blueprint application. To get the app, open a terminal and run ``mindmeld blueprint hr_assistant``.

.. warning::

   Changes by an Auto Annotator cannot be undone and Mindmeld does not backup query data. We recommend using version control software such as Github.

Default Auto Annotator: Spacy Annotator
---------------------------------------
The :mod:`mindmeld.auto_annotator` module contains an abstract :class:`Annotator` class.
This class serves as a base class for any Mindmeld Annotator including the :class:`SpacyAnnotator` class.
The :class:`SpacyAnnotator` leverages `Spacy's Named Entity Recognition <https://spacy.io/usage/linguistic-features#named-entities>`_ system to detect 21 different entities.
Some of these entities are resolvable by Duckling. 


+------------------------+-------------------------+-----------------------------------------------------------------------------+
| Supported Entities     | Resolvable by Duckling  | Examples or Definition                                                      |
+========================+=========================+=============================================================================+
| "sys_time"             | Yes                     | "today", "Tuesday, Feb 18" , "last week"                                    |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_interval"         | Yes                     | "from 9:30 to 11:00am", "Monday to Friday", "Tuesday 3pm to Wednesday 7pm"  |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_duration"         | Yes                     | "2 hours", "15 minutes", "3 days"                                           |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_number"           | Yes                     | "58", "two hundred", "1,394,345.45"                                         |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_amount-of-money"  | Yes                     | "ten dollars", "seventy-eight euros", "$58.67"                              |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_distance"         | Yes                     | "500 meters", "498 miles", "47.5 inches"                                    |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_weight"           | Yes                     | "400 pound", "3 grams", "47.5 mg"                                           |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_ordinal"          | Yes                     | "3rd place" ("3rd"), "fourth street" ("fourth"),  "5th"                     |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_percent"          | Yes                     | "four percent", "12%", "5 percent"                                          |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_org"              | No                      | "Cisco", "IBM", "Google"                                                    |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_loc"              | No                      | "Europe", "Asia", "the Alps", "Pacific ocean"                               |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_person"           | No                      | "Blake Smith", "Julia", "Andy Neff"                                         |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_gpe"              | No                      | "California", "FL", "New York City", "USA"                                  |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_norp"             | No                      | Nationalities or religious or political groups.                             |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_fac"              | No                      | Buildings, airports, highways, bridges, etc.                                |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_product"          | No                      | Objects, vehicles, foods, etc. (Not services.)                              |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_event"            | No                      | Named hurricanes, battles, wars, sports events, etc.                        |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_law"              | No                      | Named documents made into laws.                                             |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_language"         | No                      | Any named language.                                                         |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_work-of-art"      | No                      | Titles of books, songs, etc.                                                |
+------------------------+-------------------------+-----------------------------------------------------------------------------+
| "sys_other-quantity"   | No                      | "10 joules", "30 liters", "15 tons"                                         |
+------------------------+-------------------------+-----------------------------------------------------------------------------+


To detect entities in a single sentence first create an instance of the :class:`SpacyAnnotator` class.

.. code-block:: python

	from mindmeld.auto_annotator import SpacyAnnotator 
	sa = SpacyAnnotator(app_path="hr_assistant")

Then use the :meth:`parse` function.

.. code-block:: python
	
	sa.parse("Apple stock went up $10 last monday.") 

Three entities are automatically recognized and a list of dictionaries is returned. Each dictionary represents a detected entity.:

.. code-block:: python
	
	[
		{
			'body': 'Apple',
			'start': 0,
			'end': 5,
			'value': {'value': 'Apple'},
			'dim': 'sys_org'
		},
		{
			'body': '$10',
			'start': 20,
			'end': 23,
			'value': {'value': 10, 'type': 'value', 'unit': '$'},
			'dim': 'sys_amount-of-money'
		},
		{
			'body': 'last monday',
			'start': 24,
			'end': 35,
			'value': {'value': '2020-09-21T00:00:00.000-07:00',
			'grain': 'day',
			'type': 'value'},
			'dim': 'sys_time'
		}
	]

The Auto Annotator detected "Apple" as :attr:`sys_org`. Moreover, it recognized "$10" as :attr:`sys_amount-of-money` and resolved its :attr:`value` as 10 and :attr:`unit` as "$".
Lastly, it recognized "last monday" as :attr:`sys_time` and resolved its :attr:`value` to be a timestamp representing the last monday from the current date.

In general, detected entities will be represented in the following format:

.. code-block:: python

	entity = {

		"body": (substring of sentence), 
		"start": (start index), 
		"end": (end index + 1), 
		"dim": (entity type), 
		"value": (resolved value, if it exists), 

	}

To restrict the types of entities returned from the :attr:`parse()` method use the :attr:`entity_types` parameter and pass in a list of entities to restrict parsing to. By default, all entities are allowed.
For example, we can restrict the output of the previous example by doing the following:


.. code-block:: python
	
	allowed_entites = ["sys_org", "sys_amount-of-money", "sys_time"]
	sentence = "Apple stock went up $10 last monday."
	sa.parse(sentence=sentence, entity_types=allowed_entities) 

Auto Annotator Configuration
----------------------------

The :attr:`DEFAULT_AUTO_ANNOTATOR_CONFIG` shown below is the default config for an Annotator.
A custom config can be included in :attr:`config.py` by duplicating the default config and renaming it to :attr:`AUTO_ANNOTATOR_CONFIG`.
Alternatively, a custom config dictionary can be passed in directly to :class:`SpacyAnnotator` or any Annotator class upon instantiation.


.. code-block:: python

	DEFAULT_AUTO_ANNOTATOR_CONFIG = { 

		"annotator_class": "SpacyAnnotator",
		"overwrite": False, 
		"annotate": [ 
			{ 
				"domains": ".*", 
				"intents": ".*", 
				"files": ".*", 
				"entities": ".*", 
			} 
		], 
		"unannotate_supported_entities_only": True, 
		"unannotate": None, 
	}

Let's take a look at the allowed values for each setting in an Auto Annotator configuration.


``'annotator_class'`` (:class:`str`): The class in auto_annotator.py to use for annotation. By default, :class:`SpacyAnnotator` is used. 

``'overwrite'`` (:class:`bool`): Whether new annotations should overwrite existing annotations in the case of a span conflict. False by default. 

``'annotate'`` (:class:`list`): A list of annotation rules where each rule is represented as a dictionary. Each rule must have four keys: :attr:`domains`, :attr:`intents`, :attr:`files`, and :attr:`entities`.
Annotation rules are combined internally to create Regex patterns to match selected files. The character :attr:`*` can be used if all possibilities in a section are to be selected, while possibilities within
a section are expressed with the usual Regex special characters, such as :attr:`.` for any single character and :attr:`|` to represent "or". 

.. code-block:: python

	{
		"domains": "(faq|salary)", 
		"intents": ".*", 
		"files": "(train.txt|test.txt)", 
		"entities": "(sys_amount-of-money|sys_time)", 
	}

The rule above would annotate all text files named "train" or "test" in the "faq" and "salary" domains. Only sys_amount-of-money and sys_time entities would be annotated.
Internally, the above rule is combined to a single pattern: "(faq|salary)/.*/(train.txt|test.txt)" and this pattern is matched against all file paths in the domain folder of your Mindmeld application. 

.. warning::

	The order of the annotation rules matters. Each rule overwrites the list of entities to annotate for a file if the two rules include the same file. It is good practice to start with more generic rules first and then have more specific rules.
	Be sure to use the regex "or" (:attr:`|`) if applying rules at the same level of specificity. Otherwise, if written as separate rules, the latter will overwrite the former.

.. warning::
	By default, all files in all intents across all domains will be annotated with all supported entities. Before annotating consider including custom annotation rules in :attr:`config.py`. 

``'unannotate_supported_entities_only'`` (:class:`boolean`): By default, when the unannotate command is used only entities that the Annotator can annotate will be eligible for removal. 

``'unannotate'`` (:class:`list`): List of annotation rules in the same format as those used for annotation. These rules specify which entities should have their annotations removed. By default, :attr:`files` is None.

``'spacy_model'`` (:class:`str`): :attr:`en_core_web_lg` is used by default for the best performance. Alternative options are :attr:`en_core_web_sm` and :attr:`en_core_web_md`. This parameter is optional and is specific to the use of the :class:`SpacyAnnotator`.
If the selected English model is not in the current environment it will automatically be downloaded. Refer to Spacy's documentation to learn more about their `English models <https://spacy.io/models/en>`_.


Using the Auto Annotator
------------------------

The Auto Annotator can be used by importing a class that implements the :class:`Annotator` abstract class in the :mod:`auto_annotator` module or through the command-line.
We will demonstrate both approaches for unannotation and annotation using the :class:`SpacyAnnotator` class. In this tutorial we will first describe unannotation and then annotation. However, in a normal workflow you are likely to annotate first and then unannotate any annotations you are not pleased with.

Unannotate
^^^^^^^^^^
To unannotate by creating an instance of the :class:`Annotator` class, run:

.. code-block:: python

	from mindmeld.auto_annotator import SpacyAnnotator 
	sa = SpacyAnnotator(app_path="hr_assistant")

	sa.unannotate()

Alternatively, you can :attr:`unannotate` using the command-line:

.. code-block:: console

	mindmeld unannotate --app-path "hr_assistant"


If you see the following message, you need to update the unannotate parameter in your custom :attr:`AUTO_ANNOTATOR_CONFIG` dictionary in :attr:`config.py`. You can refer to the config specifications in the section above.

.. code-block:: console

	'unannotate' is None in the config. Nothing to unannotate.


Let's unannotate :attr:`sys_time` entities from the :attr:`get_date_range_aggregate` intent in the :attr:`date` domain.
To do this, we can add the following :attr:`AUTO_ANNOTATOR_CONFIG` dictionary to :attr:`config.py`.


.. code-block:: python

	AUTO_ANNOTATOR_CONFIG = { 

		"annotator_class": "SpacyAnnotator",
		"overwrite": False, 
		"annotate": [{"domains": ".*", "intents": ".*", "files": ".*", "entities": ".*"}],
		"unannotate_supported_entities_only": True, 
		"unannotate": [
			{ 
				"domains": "date", 
				"intents": "get_date_range_aggregate", 
				"files": "train.txt",
				"entities": "sys_time", 
			}
		], 
	}

.. note::

	The content of :attr:`annotate` in the config has no effect on unannotation. Similarly, :attr:`unannotate` in the config has no affect on annotation. These processes are independent and are only affected by the corresponding parameter in the config.

Before running the unannotation, we can see the first four queries in the train.txt file for the :attr:`get_date_range_aggregate` intent: 

.. code-block:: none

	{sum|function} of {non-citizen|citizendesc} people {hired|employment_action} {after|date_compare} {2005|sys_time}
	What {percentage|function} of employees were {born|dob} {before|date_compare} {1992|sys_time}?
	{us citizen|citizendesc} people with {birthday|dob} {before|date_compare} {1996|sys_time} {count|function}
	{count|function} of {eligible non citizen|citizendesc} workers {born|dob} {before|date_compare} {1994|sys_time}

After running :attr:`unannotate` we find that instances of :attr:`sys_time` have been unlabelled as expected.

.. code-block:: none

	{sum|function} of {non-citizen|citizendesc} people {hired|employment_action} {after|date_compare} 2005
	What {percentage|function} of employees were {born|dob} {before|date_compare} 1992?
	{us citizen|citizendesc} people with {birthday|dob} {before|date_compare} 1996 {count|function}
	{count|function} of {eligible non citizen|citizendesc} workers {born|dob} {before|date_compare} 1994



Annotate
^^^^^^^^

To annotate by creating an instance of the :class:`Annotator` class, run:

.. code-block:: python

	from mindmeld.auto_annotator import SpacyAnnotator 
	sa = SpacyAnnotator(app_path="hr_assistant")

	sa.annotate()

Alternatively, you can :attr:`annotate` using the command-line:

.. code-block:: console

	mindmeld annotate --app-path "hr_assistant"

Let's annotate :attr:`sys_person` entities from the :attr:`get_hierarchy_up` intent in the :attr:`hierarchy` domain.
To do this, we can add the following :attr:`AUTO_ANNOTATOR_CONFIG` dictionary to :attr:`config.py`.
Notice that we are setting :attr:`overwrite` to True since we want to replace the existing custom entity label, :attr:`name`.

.. code-block:: python

	AUTO_ANNOTATOR_CONFIG = { 

		"annotator_class": "SpacyAnnotator",
		"overwrite": True, 
		"annotate": [
			{ 
				"domains": "hierarchy", 
				"intents": "get_hierarchy_up", 
				"files": "train.txt",
				"entities": "sys_person", 
			}
		],
		"unannotate_supported_entities_only": True, 
		"unannotate": None
	}

Before running the annotation, we can see the first four queries in the train.txt file for the :attr:`get_hierarchy_up` intent: 

.. code-block:: none

	I wanna get a list of all of the employees that are currently {manage|manager} {caroline|name}
	I wanna know {Tayana Jeannite|name}'s person in {leadership|manager} of her?
	is it correct to say that {Angela|name} is a {boss|manager}?
	who all is {management|manager} of {tayana|name}

After running :attr:`annotate` we find that instances of :attr:`sys_person` have been labelled and have overwritten previous instances of the custom entity, :attr:`name`.

.. code-block:: none

	I wanna get a list of all of the employees that are currently {manage|manager} {caroline|sys_person}
	I wanna know {Tayana Jeannite|sys_person}'s person in {leadership|manager} of her?
	is it correct to say that {Angela|sys_person} is a {boss|manager}?
	who all is {management|manager} of {tayana|sys_person}


Creating a Custom Annotator
---------------------------
The :class:`SpacyAnnotator` is a subclass of the abstract base class :class:`Annotator`.
The functionality for annotating and unannotating files is contained in :class:`Annotator` itself.
A developer simply needs to implement two methods to create a custom annotator.


Custom Annotator Boilerplate Code
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This section includes boilerplate code to build a :class:`CustomAnnotator` class to add to :attr:`auto_annotator.py`
There are two "TODO"s. To implement a :class:`CustomAnnotator` class a developer has to implement the :meth:`parse` and :meth:`valid_entity_check` methods.

.. code-block:: python

	class CustomAnnotator(Annotator):
		""" Custom Annotator class used to generate annotations.
		"""

		def __init__(self, app_path, config=None):
			super().__init__(app_path=app_path, config=config)
			
			# Add additional attributes if needed

		def parse(self, sentence, entity_types=None):
			""" 
			Args:
				sentence (str): Sentence to detect entities.
				entity_types (list): List of entity types to parse. If None, all
					possible entity types will be parsed.
			Returns: entities (list): List of entity dictionaries.
			"""

			# TODO: Add custom parse logic

			return entities

		def valid_entity_check(self, entity):
			""" 
			Args: entity (str): Name of entity to annotate.
			Returns: bool: Whether entity is valid.
			"""
			entity = entity.lower().strip()
			supported_entities = [

			# TODO: Add list of supported entity names
			
			]
			return entity in supported_entities

Entities returned by :attr:`parse()` must have the following format:

.. code-block:: python

	entity = { 
		"body": (substring of sentence), 
		"start": (start index), 
		"end": (end index + 1), 
		"dim": (entity type), 
		"value": (resolved value, if it exists), 
	}

Registering Annotator to Enable command-line Use
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In order to use our :class:`CustomAnnotator` when running annotation/unannotation commands from the command-line, we must add the following line to the bottom of the :attr:`auto_annotator.py` file to register the class and ensure that it loads in the :attr:`cli.py` file.

.. code-block:: python
	
	register_annotator("CustomAnnotator", CustomAnnotator)

Be sure to update the :class:`annotator_class` parameter in the config with the registered name of your custom annotator.

.. code-block:: python

	AUTO_ANNOTATOR_CONFIG = { 
		...
		"annotator_class": "CustomAnnotator",
		...
	}

Now we can :attr:`annotate` with our custom annotator using the command-line:

.. code-block:: console

	mindmeld annotate --app-path "hr_assistant"


Getting Custom Parameters from the Config
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:attr:`spacy_model` is an example of an optional parameter in the config that is relevant only for a specific :class:`Annotator` class.

.. code-block:: python

	AUTO_ANNOTATOR_CONFIG = { 
		... 
		"spacy_model": "en_core_web_md",
		... 
	}

:class:`SpacyAnnotator` checks if :attr:`spacy_model` exists in the config, and if it doesn't, it will use the default value of "en_core_web_lg".

.. code-block:: python

	class SpacyAnnotator(Annotator):
		""" Annotator class that uses spacy to generate annotations.
		"""

		def __init__(self, app_path, config=None):
			super().__init__(app_path=app_path, config=config)

			self.model = self.config.get("spacy_model", "en_core_web_lg")

Custom parameters for custom annotators can be implemented in a similar fashion.