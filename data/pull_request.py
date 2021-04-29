from github import Github

git = Github()


class PullRequest:
    def __init__(self, repo, number):
        self.repo = git.get_repo(repo)
        self.number = number
        self.pull_request = self.repo.get_pull(number)
        self.changed_files_names = []

    def set_changed_files(self):
        files = self.pull_request.get_files()
        for file in files:
            self.changed_files_names.append(file.filename)


class Comparator:
    pr1: "PullRequest"
    pr2: "PullRequest"
    files_similarity: float
    files_intersect: int

    def __init__(self, pr1: "PullRequest", pr2: "PullRequest"):
        self.pr1 = pr1
        self.pr2 = pr2

    def compute_files_similarity(self):
        self.files_similarity = self.compute_jaccard(self.pr1.changed_files_names, self.pr2.changed_files_names)
        self.files_intersect = 0
        for file in self.pr1.changed_files_names:
            if file in self.pr2.changed_files_names:
                self.files_intersect += 1

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
