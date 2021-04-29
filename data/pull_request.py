from github import Github

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

git = Github()
sw = stopwords.words('english')


class PullRequest:
    changed_files_names: set
    textual_tokens: set

    def __init__(self, repo, number):
        self.repo = git.get_repo(repo)
        self.number = number
        self.pull_request = self.repo.get_pull(number)

    def set_changed_files(self):
        files = self.pull_request.get_files()
        for file in files:
            self.changed_files_names.add(file.filename)

    @staticmethod
    def tokenize(text):
        tokens = word_tokenize(text)
        tokens_set = {w for w in tokens if w not in sw}
        return tokens_set

    def text_tokenize(self):
        title_tokens = self.tokenize(self.pull_request.title)
        description_tokens = self.tokenize(self.pull_request.body)
        self.textual_tokens = title_tokens.union(description_tokens)


class Comparator:
    pr1: "PullRequest"
    pr2: "PullRequest"
    files_similarity: float
    files_intersect: int
    textual_similarity: float

    def __init__(self, pr1: "PullRequest", pr2: "PullRequest"):
        self.pr1 = pr1
        self.pr2 = pr2

    def compute_files_similarity(self):
        self.files_similarity = self.compute_jaccard(self.pr1.changed_files_names, self.pr2.changed_files_names)
        self.files_intersect = 0
        for file in self.pr1.changed_files_names:
            if file in self.pr2.changed_files_names:
                self.files_intersect += 1

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
