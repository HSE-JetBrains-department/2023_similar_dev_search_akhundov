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
    Get name of the repository of tree-sitter bindings inside build dir
    :param url: GitHub repository URL
    :return: name
    """
    # Take the last part between slashes (not to include org name not to nest dirs)
    project_name = url.split('/')[-1]
    clean_project_name = project_name.split('-')[-1]  # to avoid symbol errors
    return clean_project_name


class TreeSitterExtractor:
    """
    Stage to prepare tree-sitter downloading and building all bindings needed and
    crafting parsers for them
    """

    # String the GitHub Repository URL starts with
    # Used to strip the repository url to get the correct name for bindings
    GITHUB_URL_PREFIX = "https://github.com/"

    # Default associations from language name to GitHub Repository of the bindings URL
    # Key must be one of enry classified languages names
    DEFAULT_LANG_BINDINGS = {
        'Go': 'https://github.com/tree-sitter/tree-sitter-go',
        'Java': 'https://github.com/tree-sitter/tree-sitter-java',
        'Python': 'https://github.com/tree-sitter/tree-sitter-python'
    }

    # Name of the compiled bindings shared object file
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
        "Ruby": {"identifier", "constant", "symbol"},
        "TypeScript": {"identifier", "property_identifier",
                       "shorthand_property_identifier", "type_identifier"},
        "TSX": {"identifier", "property_identifier",
                "shorthand_property_identifier", "type_identifier"},
        "PHP": {"name"},
        "C#": {"identifier"},
        "C": {"identifier", "field_identifier", "type_identifier"},
        "Shell": {"variable_name", "command_name"},
        "Rust": {"identifier", "field_identifier", "type_identifier"}
    }

    def __init__(self,
                 build_dir_path: str = "build",
                 lang_bindings: Optional[Dict[str, str]] = None):
        """
        Initialize tree sitter prepare stage
        :param build_dir_path: path to directory to store build files for bindings
        :param lang_bindings: dict from the name of the language
         to the GitHub repository URL of its tree-sitter bindings.
         Key must be one of enry classified languages names
        """
        self.build_dir_path = Path(build_dir_path)

        self.lang_bindings = lang_bindings
        if self.lang_bindings is None:
            # If no binding repos provided use default ones
            self.lang_bindings = TreeSitterExtractor.DEFAULT_LANG_BINDINGS

        # dict from language name (e.g. python) to its tree-sitter language object
        self.langs: Dict[str, Language] = {}
        # dict from language name (e.g. python) to its parser
        self.parsers: Dict[str, Parser] = {}

        # Cache language-related functions
        self._build_language_parser = \
            PipelineCache.memory.cache(self._make_language_and_parser)
        self._clone_language_binding = \
            PipelineCache.memory.cache(self._clone_language_binding)

    def prepare(self) -> None:
        """
        Clone language bindings then build them.
        Finally, make parsers for all the languages and store them in the context
        for further use
        """
        lang_progress = tqdm(self.lang_bindings.keys(), 'Clone tree-sitter bindings')
        for lang in lang_progress:
            lang_progress.set_postfix_str(lang)
            self._clone_language_binding(lang)

        lang_progress.set_description('Building...')
        Language.build_library(output_path=str(self._get_shared_object_file_path()),
                               repo_paths=[str(self._get_repo_build_path(url))
                                           for url in self.lang_bindings.values()])

        for lang in self.lang_bindings:
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
        counter: Counter[str] = Counter()

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
                    counter.update([identifier_name.decode(encoding='utf-8')])
                traverse_extract(child)

        # Extract all the identifiers traversing obtained source code tree
        traverse_extract(parsed_tree.root_node)
        return counter

    def _clone_language_binding(self, lang: str):
        """
        Clone language bindings repository
        :param lang: language to clone bindings for
        """
        bindings_repo_url = self.lang_bindings[lang]
        clone_path = self._get_repo_build_path(bindings_repo_url)
        if not clone_path.exists():
            clone_path.mkdir(parents=True)
            Repo.clone_from(url=bindings_repo_url, to_path=clone_path)

    def _make_language_and_parser(self, lang: str) -> Tuple[Language, Parser]:
        """
        Obtain tree-sitter language and its parser
        :param lang: language name to obtain tree-sitter language and parser for
        :return: language and its parser
        """
        lang_repo_url = self.lang_bindings[lang]
        tree_sitter_lang = Language(
            self._get_shared_object_file_path(),
            _get_repo_build_name(lang_repo_url))
        lang_parser = Parser()
        lang_parser.set_language(tree_sitter_lang)
        return tree_sitter_lang, lang_parser

    def _get_repo_build_path(self, url: str) -> Path:
        """
        Get local fs path to repository of tree-sitter bindings inside build dir
        :param url: GitHub repository URL
        :return: path to dir inside build dir
        """
        return self.build_dir_path / _get_repo_build_name(url)

    def _get_shared_object_file_path(self) -> Path:
        """
        :return: path to built shared object file from tree-sitter
        """
        return self.build_dir_path / TreeSitterExtractor.SHARED_OBJECT_FILENAME
