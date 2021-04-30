import os
import re
from enum import Enum

import requests
from bs4 import BeautifulSoup
from github import Github
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

github_token = os.getenv("GITHUB_TOKEN")
git = Github(github_token)
sw = stopwords.words('english')
useless_keywords = {'for', 'type', 'len', 'length', 'this'}  # Could be completed


class PullRequest:
    def __init__(self, repo, number):
        self.repo_name = repo
        self.repo = git.get_repo(repo)
        self.pr_number = number
        self.pull_request = self.repo.get_pull(number)
        self.changed_files_names = set()
        self.textual_tokens = set()
        self.issue_ids = set()
        self.patch_added_words = set()
        self.set_changed_files()
        self.text_tokenize()
        self.set_issues()
        self.set_added_words()

    def set_changed_files(self):
        files = self.pull_request.get_files()
        for file in files:
            self.changed_files_names.add(file.filename)

    def set_added_words(self):
        r = requests.get(self.pull_request.diff_url)
        if r.status_code != 200:
            return
        added_lines_words = set()
        deleted_lines_words = set()
        lines = r.text.split("\n")
        for line in lines:
            tokens = set(re.findall(r"[\w']+", line))
            discarded_tokens = useless_keywords
            for token in tokens:
                if len(token) < 2:
                    discarded_tokens.add(token)
            tokens = tokens.difference(discarded_tokens)
            if line.startswith("+"):
                added_lines_words.update(tokens)
            if line.startswith("-"):
                deleted_lines_words.update(tokens)

        self.patch_added_words = added_lines_words.difference(deleted_lines_words)

    @staticmethod
    def tokenize(text):
        tokens = word_tokenize(text)
        tokens_set = {w for w in tokens if w not in sw}
        return tokens_set

    def set_issues(self):
        title_words = self.pull_request.title.split(" ")
        # Simplest check I could do! just checking whether there is a numeric in the PR issue title or not.
        # It will not be harmful if there exists a number other than issue id, since most probably that number will
        # not exist in other pr titles and if it does, there maybe a duplication too. As Simple as I Could!
        for word in title_words:
            if word.isnumeric():
                self.issue_ids.add(word)
                continue
            if word[0:-1].isnumeric():  # Because of existence of ) or : at the end of number
                self.issue_ids.add(word[0:-1])

        # Check for existence of GitHub Issue Tracker
        r = requests.get(f"https://github.com/{self.repo_name}/pull/{self.pr_number}")
        if r.status_code != 200:
            return
        soup = BeautifulSoup(r.text, 'html.parser')
        issue_form = soup.find("form", {"aria-label": re.compile('Link issues')})
        if not issue_form:
            return
        issues_links = [i["href"] for i in issue_form.find_all("a")]
        for issue_link in issues_links:
            self.issue_ids.add(issue_link.split("/")[-1])

    def text_tokenize(self):
        # TODO: Add commit messages too
        title_tokens = self.tokenize(self.pull_request.title)
        description_tokens = self.tokenize(self.pull_request.body)
        self.textual_tokens = title_tokens.union(description_tokens)


class Comparator:
    pr1: "PullRequest"
    pr2: "PullRequest"
    files_similarity: float
    files_intersect: int
    textual_similarity: float
    issues_similarity: "IssueSimilarity"
    added_words_similarity: float

    class IssueSimilarity(Enum):
        UNKNOWN = 0  # At least one of the pull requests does not have an issue
        HIGH_SIMILAR = 1  # All issues most be similar
        LOW_SIMILAR = 2  # Just one similar issue is enough
        DISSIMILAR = 3  # Not even one similar issue

    def __init__(self, pr1: "PullRequest", pr2: "PullRequest"):
        self.pr1 = pr1
        self.pr2 = pr2
        self.compute_files_similarity()
        self.compute_issues_similarity()
        self.compute_textual_similarity()

    def compute_files_similarity(self):
        self.files_similarity = self.compute_jaccard(self.pr1.changed_files_names, self.pr2.changed_files_names)
        self.files_intersect = 0
        for file in self.pr1.changed_files_names:
            if file in self.pr2.changed_files_names:
                self.files_intersect += 1

    def compute_issues_similarity(self):
        self.issues_similarity = self.IssueSimilarity.UNKNOWN
        if (not self.pr1.issue_ids) or (not self.pr2.issue_ids):
            return

        if self.pr1.issue_ids == self.pr2.issue_ids:
            self.issues_similarity = self.IssueSimilarity.HIGH_SIMILAR
            return

        for issue in self.pr1.issue_ids:
            if issue in self.pr2.issue_ids:
                self.issues_similarity = self.IssueSimilarity.LOW_SIMILAR
                return

    @staticmethod
    def compute_tokens_similarity(tokens1, tokens2):
        all_tokens = tokens1.union(tokens2)
        if len(tokens1) == 0 and len(tokens2) == 0:
            return 0.2  # Just testing
        if len(tokens1) == 0 or len(tokens2) == 0:
            return 0
        l1 = []
        l2 = []
        for w in all_tokens:
            if w in tokens1:
                l1.append(1)  # Replace with tf-idf
            else:
                l1.append(0)
            if w in tokens2:
                l2.append(1)
            else:
                l2.append(0)
        c = 0
        for i in range(len(all_tokens)):
            c += l1[i] * l2[i]
        cosine = c / float((sum(l1) * sum(l2)) ** 0.5)
        return cosine

    def compute_textual_similarity(self):
        self.textual_similarity = self.compute_tokens_similarity(self.pr1.textual_tokens, self.pr2.textual_tokens)
        self.added_words_similarity = self.compute_tokens_similarity(self.pr1.patch_added_words,
                                                                     self.pr2.patch_added_words)

    @staticmethod
    def compute_jaccard(first_set, second_set):
        intersection = set()
        union = set()
        for element in first_set:
            if element in second_set:
                intersection.add(element)
            union.add(element)
        for element in second_set:
            union.add(element)

        return len(intersection) / len(union)

    def compute_similarity_score(self):
        max_possible_sim = 0
        issue_similarity_score = 0
        if self.issues_similarity == self.IssueSimilarity.HIGH_SIMILAR:
            issue_similarity_score = 1
        elif self.issues_similarity == self.IssueSimilarity.LOW_SIMILAR:
            issue_similarity_score = 0.75
        elif self.issues_similarity == self.IssueSimilarity.DISSIMILAR:
            issue_similarity_score = 0
        if self.issues_similarity != self.IssueSimilarity.UNKNOWN:
            max_possible_sim += 1
        max_possible_sim += 1 + 1 + 1  # For Files Similarity, Textual Similarity and Added Words Similarity
        similarity = issue_similarity_score + self.files_similarity + self.textual_similarity + self.added_words_similarity
        return float(similarity / max_possible_sim)

    def __str__(self):
        return f"Files Similarity: {self.files_similarity}\n" \
               f"Files Intersect: {self.files_intersect}\n" \
               f"Issues Similarity: {self.issues_similarity.name}\n" \
               f"Textual (Title and Description) Similarity: {self.textual_similarity}\n" \
               f"Added Words Similarity: {self.added_words_similarity}\n" \
               f"Total Similarity: {self.compute_similarity_score()}"
