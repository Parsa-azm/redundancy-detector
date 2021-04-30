from data.pull_request import PullRequest, Comparator


if __name__ == "__main__":
    with open('data/duplicated_pairs_1.txt', 'r') as source:
        for line in source:
            parts = line.split()
            repo = parts[0]
            pr_number_1 = parts[1]
            pr_number_2 = parts[2]
            pr1 = PullRequest(repo, int(pr_number_1))
            pr2 = PullRequest(repo, int(pr_number_2))
            comparator = Comparator(pr1, pr2)
            print(f"Similarities of Pull Request no.{pr_number_1} and Pull Request no.{pr_number_2} from Repo {repo}:")
            print(comparator)
