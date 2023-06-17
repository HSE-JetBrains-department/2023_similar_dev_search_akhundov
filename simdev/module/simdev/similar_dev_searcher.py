from collections import defaultdict
from typing import Counter, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from simdev.module.git.repo_info_extractor import DevInfo


class SimilarDevSearcher:
    """
    Class to search for similar developers.
    Utilizes pandas, sklearn and numpy to transform DevInfo
    data and search for similarities using cosine similarity
    """

    def __init__(self, dev_info: DevInfo, max_results_count: int = 10):
        """
        Initializer sim-dev discoverer
        :param dev_info: information about developers: changes in repositories:
        files, in-code identifiers, languages
        :param max_results_count: how many developers at maximum to return (compute)
        """
        self.dev_info = dev_info
        self.max_results_count = max_results_count

    def search(self, dev_email: str) -> Dict[str, float]:
        """
        Discover similar developers
        :param dev_email: Email of the developer to find similar developers to
        :return: dict from another developer's email to similarity score
        (how similar the developer is to the original)
        """
        identifier_vectors, identifier_feature_names = self._vectorize_identifiers()
        lang_vectors, lang_feature_names = self._vectorize_langs()
        df = pd.DataFrame(
            data=np.hstack((identifier_vectors, lang_vectors)),
            columns=np.hstack((identifier_feature_names, lang_feature_names)),
            index=self.dev_info.keys()
        )

        # Compute scores filtering dataframe
        df_others = df[df.index != dev_email]
        df_self = df[df.index == dev_email]
        scores = cosine_similarity(df_others, df_self)

        # "Join" emails and scores, sort it by score and convert to dict
        email_score_array = np.column_stack((df_others.index, scores))
        sorted_results = dict(sorted(email_score_array,
                                     key=lambda row: row[1],
                                     reverse=True)[:self.max_results_count])
        return sorted_results

    def _vectorize_identifiers(self) -> Tuple[np.matrix[float], np.ndarray[str]]:
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

    def _vectorize_langs(self) -> Tuple[np.matrix[int], np.ndarray[str]]:
        """
        Collect languages and form a matrix out of them for all the developers
        using DictVectorizer
        :return: tuple of: vectors and feature (language) names
        """
        vectorizer = DictVectorizer()
        lang_dict: Dict[str, Counter] = defaultdict(Counter)
        for dev_email, repos_info in self.dev_info.items():
            for repo, repo_info in repos_info.items():
                lang_dict[dev_email].update(**repo_info['langs'])

        lang_vectors = vectorizer.fit_transform(lang_dict.values()).todense()
        lang_feature_names = vectorizer.get_feature_names_out()
        return lang_vectors, lang_feature_names
