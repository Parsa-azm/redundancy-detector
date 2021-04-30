import re
from enum import Enum

import requests
from bs4 import BeautifulSoup
from github import Github
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

git = Github()
sw = stopwords.words('english')
useless_keywords = {'for', 'type', 'len', 'length', 'this'}  # Could be completed


class PullRequest:
    changed_files_names: set
    textual_tokens: set
    issue_ids: set
    patch_added_words: set

    def __init__(self, repo, number):
        self.repo_name = repo
        self.repo = git.get_repo(repo)
        self.pr_number = number
        self.pull_request = self.repo.get_pull(number)

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
        counter = 0
        # Simplest check I could do! just checking whether there is a numeric in first 3 words of the PR issue title or
        # not. It will not be harmful if there exists a number other than issue id, since most probably that number will
        # not exist in other pr titles and if it does, there maybe a duplication too. As Simple as I Could!
        for word in title_words:
            if word.isnumeric():
                self.issue_ids.add(word)
            counter += 1
            if counter > 3:
                break

        # Check for existence of GitHub Issue Tracker
        r = requests.get(f"https://github.com/{self.repo_name}/pull/{self.pr_number}")
        if r.status_code != 200:
            return
        soup = BeautifulSoup(r.text, 'html.parser')
        issue_form = soup.find("form", {"aria-label": re.compile('Link issues')})
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

    class IssueSimilarity(Enum):
        UNKNOWN = 0  # At least one of the pull requests does not have an issue
        HIGH_SIMILAR = 1  # All issues most be similar
        LOW_SIMILAR = 2  # Just one similar issue is enough
        DISSIMILAR = 3  # Not even one similar issue

    def __init__(self, pr1: "PullRequest", pr2: "PullRequest"):
        self.pr1 = pr1
        self.pr2 = pr2

    def compute_files_similarity(self):
        self.files_similarity = self.compute_jaccard(self.pr1.changed_files_names, self.pr2.changed_files_names)
        self.files_intersect = 0
        for file in self.pr1.changed_files_names:
            if file in self.pr2.changed_files_names:
                self.files_intersect += 1

    def compute_issues_similarity(self):
        if (not self.pr1.issue_ids) or (not self.pr2.issue_ids):
            self.issues_similarity = self.IssueSimilarity.UNKNOWN
            return

        if self.pr1.issue_ids == self.pr2.issue_ids:
            self.issues_similarity = self.IssueSimilarity.HIGH_SIMILAR
            return

        for issue in self.pr1.issue_ids:
            if issue in self.pr2.issue_ids:
                self.issues_similarity = self.IssueSimilarity.LOW_SIMILAR
                return

    def compute_textual_similarity(self):
        all_tokens = self.pr1.textual_tokens.union(self.pr2.textual_tokens)
        l1 = []
        l2 = []

        for w in all_tokens:
            if w in self.pr1.textual_tokens:
                l1.append(1)  # Replace with tf-idf
            else:
                l1.append(0)
            if w in self.pr2.textual_tokens:
                l2.append(1)
            else:
                l2.append(0)
        c = 0
        for i in range(len(all_tokens)):
            c += l1[i] * l2[i]
        cosine = c / float((sum(l1) * sum(l2)) ** 0.5)
        self.textual_similarity = cosine

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
