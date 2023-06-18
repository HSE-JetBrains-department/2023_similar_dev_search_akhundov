from collections import Counter
from pathlib import Path
from typing import Dict, Optional, Tuple

from git import Repo
from tqdm import tqdm
import tree_sitter
from tree_sitter import Language, Parser

from simdev.util.pipeline import PipelineCache


def _get_repo_build_name(url: str) -> str:
    """
    Get name of the repository of tree-sitter grammar inside build dir
    :param url: GitHub repository URL
    :return: name
    """
    # Take the last part between slashes (not to include org name not to nest dirs)
    project_name = url.split('/')[-1]
    clean_project_name = project_name.split('-')[-1]  # to avoid symbol errors
    return clean_project_name


class TreeSitterExtractor:
    """
    Stage to prepare tree-sitter downloading and building all the grammars needed and
    crafting parsers for them
    """

    # Default associations from language name to URL of Git repository for its grammar
    # Key must be one of enry classified languages names
    DEFAULT_LANG_GRAMMAR = {
        'JavaScript': 'https://github.com/tree-sitter/tree-sitter-javascript',
        'Python': 'https://github.com/tree-sitter/tree-sitter-python',
        'Java': 'https://github.com/tree-sitter/tree-sitter-java',
        'Go': 'https://github.com/tree-sitter/tree-sitter-go',
        'C++': 'https://github.com/tree-sitter/tree-sitter-cpp',
        'C': 'https://github.com/tree-sitter/tree-sitter-c',
        'Shell': 'https://github.com/tree-sitter/tree-sitter-bash',
        'Rust': 'https://github.com/tree-sitter/tree-sitter-rust'
    }

    # Name of the compiled grammar shared object file
    SHARED_OBJECT_FILENAME = "languages.so"

    # Tree-sitter language-specific node types for identifiers
    # Source: https://github.com/JetBrains-Research/buckwheat
    IDENTIFIER_NODE_TYPES = {
        "JavaScript": {"identifier", "property_identifier",
                       "shorthand_property_identifier"},
        "Python": {"identifier"},
        "Java": {"identifier", "type_identifier"},
        "Go": {"identifier", "field_identifier", "type_identifier"},
        "C++": {"identifier", "namespace_identifier", "field_identifier",
                "type_identifier"},
        "C": {"identifier", "field_identifier", "type_identifier"},
        "Shell": {"variable_name", "command_name"},
        "Rust": {"identifier", "field_identifier", "type_identifier"}
    }

    def __init__(self,
                 build_dir_path: str = "build",
                 lang_grammars: Optional[Dict[str, str]] = None):
        """
        Initialize tree sitter prepare stage
        :param build_dir_path: path to directory to store build files for grammars
        :param lang_grammars: dict from the name of the language
         to the GitHub repository URL of its tree-sitter grammars.
         Key must be one of enry classified languages names
        """
        self.build_dir_path = Path(build_dir_path)

        self.lang_grammars = lang_grammars
        if self.lang_grammars is None:
            # If no grammar repos provided use default ones
            self.lang_grammars = TreeSitterExtractor.DEFAULT_LANG_GRAMMAR

        # Dict from language name (e.g. python) to its tree-sitter language object
        self.langs: Dict[str, Language] = {}
        # Dict from language name (e.g. python) to its parser
        self.parsers: Dict[str, Parser] = {}

        # Cache language-related functions
        self._build_language_parser = \
            PipelineCache.memory.cache(self._make_language_and_parser)
        self._clone_language_grammar = \
            PipelineCache.memory.cache(self._clone_language_grammar)

    def prepare(self) -> None:
        """
        Clone language grammars then build them.
        Finally, make parsers for all the languages and store them in the context
        for further use
        """
        lang_progress = tqdm(self.lang_grammars.keys(), 'Clone tree-sitter grammar')
        for lang in lang_progress:
            lang_progress.set_postfix_str(lang)
            self._clone_language_grammar(lang)

        lang_progress.set_description('Building...')
        Language.build_library(output_path=str(self._get_shared_object_file_path()),
                               repo_paths=[str(self._get_repo_build_path(url))
                                           for url in self.lang_grammars.values()])

        for lang in self.lang_grammars:
            tree_sitter_lang, tree_sitter_lang_parser = \
                self._make_language_and_parser(lang)
            self.parsers[lang] = tree_sitter_lang_parser
            self.langs[lang] = tree_sitter_lang

    def extract_identifiers(self,
                            prog_language: str,
                            content: bytes) -> Optional[Counter]:
        """
        Extract information about all the identifiers in the source code
        Perform tree-sitter query, fetch and store results
        :param prog_language: file's programming language classified by enry
        :param content: raw contents of the file
        """
        if content is None:
            return None
        if prog_language is None:
            # There's no need to extract identifiers
            # if there is no classified programming language
            return None
        if prog_language not in self.parsers or prog_language not in self.langs:
            # We don't know how to work with the given language
            return None

        # Getting suitable parser and parse the code
        parser = self.parsers[prog_language]
        parsed_tree = parser.parse(content)
        identifier_counter: Counter[str] = Counter()

        def traverse_extract(node: Optional[tree_sitter.Node]):
            """
            Traversing all over the nodes in AST, finding identifiers
            and extracting their names
            :param node to perform the traverse from
            """
            if node is None:
                return
            for child in node.children:
                if child.type in \
                        TreeSitterExtractor.IDENTIFIER_NODE_TYPES[prog_language]:
                    identifier_name = content[child.start_byte:child.end_byte]
                    identifier_counter.update([identifier_name.decode()])
                traverse_extract(child)

        # Extract all the identifiers traversing obtained source code tree
        traverse_extract(parsed_tree.root_node)
        return identifier_counter

    def _clone_language_grammar(self, lang: str):
        """
        Clone language grammar repository
        :param lang: language to clone grammar for
        """
        lang_grammar_repo_url = self.lang_grammars[lang]
        clone_path = self._get_repo_build_path(lang_grammar_repo_url)
        if not clone_path.exists():
            clone_path.mkdir(parents=True)
            Repo.clone_from(url=lang_grammar_repo_url, to_path=clone_path)

    def _make_language_and_parser(self, lang: str) -> Tuple[Language, Parser]:
        """
        Obtain tree-sitter language and its parser
        :param lang: language name to obtain tree-sitter language and parser for
        :return: language and its parser
        """
        lang_grammar_repo_url = self.lang_grammars[lang]
        tree_sitter_lang = Language(
            self._get_shared_object_file_path(),
            _get_repo_build_name(lang_grammar_repo_url))
        lang_parser = Parser()
        lang_parser.set_language(tree_sitter_lang)
        return tree_sitter_lang, lang_parser

    def _get_repo_build_path(self, url: str) -> Path:
        """
        Get local fs path to repository of tree-sitter grammar inside build dir
        :param url: GitHub repository URL
        :return: path to dir inside build dir
        """
        return self.build_dir_path / _get_repo_build_name(url)

    def _get_shared_object_file_path(self) -> Path:
        """
        :return: path to built shared object file from tree-sitter
        """
        return self.build_dir_path / TreeSitterExtractor.SHARED_OBJECT_FILENAME
