from collections import Counter, defaultdict
from typing import Dict, List, Tuple, TypedDict

import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from simdev.module.git.repo_info_extractor import DevInfo

# Info about a similar developer
SimilarDevInfo = TypedDict('SimilarDevInfo', {
    'score': float,  # Similarity score
    'identifiers': Dict[str, int],  # Most commonly used identifiers
    'repos': Dict[str, int],  # Most contributed to based on file count
    'langs': Dict[str, int]  # Most used languages based on files
})


class SimilarDevSearcher:
    """
    Class to search for similar developers.
    Utilizes pandas, sklearn and numpy to transform DevInfo
    data and search for similarities using cosine similarity
    """

    def __init__(self, dev_info: DevInfo, max_results_count: int = 10,
                 top_size: int = 5):
        """
        Initializer sim-dev discoverer
        :param dev_info: Information about developers: changes in repositories:
        files, in-code identifiers, languages
        :param max_results_count: How many developers at maximum to return (compute)
        :param top_size: Size of top (top-n) languages, repositories, identifiers
        """
        self.dev_info = dev_info
        self.max_results_count = max_results_count
        self.top_size = top_size

    def search(self, dev_email: str) -> Dict[str, SimilarDevInfo]:
        """
        Discover similar developers
        :param dev_email: Email of the developer to find similar developers to
        :return: Dict from another developer's email to: score - similarity score
        (how similar the developer is to the original), identifiers - most
        frequently used identifiers, repositories - top-n repositories based on
        file count
        """
        identifier_vectors, identifier_feature_names = self._vectorize_identifiers()
        lang_vectors, lang_feature_names = self._vectorize_langs()
        df = pd.DataFrame(
            data=np.hstack((identifier_vectors, lang_vectors)),
            columns=np.hstack((identifier_feature_names, lang_feature_names)),
            index=self.dev_info.keys())
        sorted_scores = self._compute_sorted_scores(df, dev_email)

        # Form and fill the final dict of results
        results: Dict[str, SimilarDevInfo] = defaultdict(lambda: SimilarDevInfo(
            score=0.0,
            identifiers=dict(),
            langs=dict(),
            repos=dict()
        ))
        for dev_email in sorted_scores:
            similar_info = results[dev_email]
            similar_info['score'] = sorted_scores[dev_email]
            self._write_top_params(dev_email, similar_info)
        return results

    def _vectorize_identifiers(self) -> Tuple[np.matrix, np.ndarray]:
        """
        Collect identifier frequencies, unroll them to text and
        perform tfidf vectorization on identifier names
        :return: tuple of: vectors and feature (identifier) names
        """
        vectorizer = TfidfVectorizer()
        identifier_sentences: List[str] = []
        for dev_email, repos_info in self.dev_info.items():
            parts: List[str] = []
            for repo, repo_info in repos_info.items():
                unrolled_identifiers = [
                    identifier
                    for (identifier, times) in repo_info['identifiers'].items()
                    for _ in range(times)
                ]
                parts.append(' '.join(unrolled_identifiers))
            identifier_sentences.append(' '.join(parts))

        identifier_vectors = vectorizer.fit_transform(identifier_sentences).todense()
        identifier_feature_names = vectorizer.get_feature_names_out()
        return identifier_vectors, identifier_feature_names

    def _vectorize_langs(self) -> Tuple[np.matrix, np.ndarray]:
        """
        Collect languages and form a matrix out of them for all the developers
        using DictVectorizer
        :return: Tuple of: vectors and feature (language) names
        """
        vectorizer = DictVectorizer()
        lang_dict: Dict[str, Counter] = defaultdict(Counter)
        for dev_email, repos_info in self.dev_info.items():
            for repo, repo_info in repos_info.items():
                lang_dict[dev_email].update(**repo_info['langs'])

        lang_vectors = vectorizer.fit_transform(lang_dict.values()).todense()
        lang_feature_names = vectorizer.get_feature_names_out()
        return lang_vectors, lang_feature_names

    def _compute_sorted_scores(self,
                               df: pd.DataFrame,
                               dev_email: str) -> Dict[str, float]:
        """
        Compute sorted similarity scores using cosine similarity
        :param df: Prepared dataframe
        :param dev_email: Email of the developer to find similar to
        :return: Dict from developer's email to its score.
        Items are sorted by value (The highest score - first key)
        """
        # Compute scores filtering dataframe
        scores = cosine_similarity(df[df.index != dev_email], df[df.index == dev_email])
        # "Join" emails and scores, sort it by score and convert to dict
        email_score_array = np.column_stack((df[df.index != dev_email].index, scores))
        sorted_scores: Dict[str, float] = \
            dict(sorted(email_score_array,
                        key=lambda row: row[1],
                        reverse=True)[:self.max_results_count])
        return sorted_scores

    def _write_top_params(self, dev_email: str, result: SimilarDevInfo) -> None:
        """
        Write most frequently used params: languages, identifiers
        and repositories (based on the file count modified in them)
        :param dev_email: dev email to write info about
        :param result: to write top params to
        :return: dict of most common identifiers
        """
        identifiers_counter = Counter({})
        langs_counter = Counter({})
        repos_counter = Counter({})
        for repo, repo_info in self.dev_info[dev_email].items():
            identifiers_counter.update(repo_info['identifiers'])
            langs_counter.update(repo_info['langs'])
            repos_counter[repo] = len(repo_info['files'])
        result['langs'] = dict(langs_counter.most_common(self.top_size))
        result['identifiers'] = dict(identifiers_counter.most_common(self.top_size))
        result['repos'] = dict(repos_counter.most_common(self.top_size))
