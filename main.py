from pull_request import PullRequest, Comparator


def compare(repo, pr_num_1, pr_num_2):
    pr1 = PullRequest(repo, int(pr_num_1))
    pr2 = PullRequest(repo, int(pr_num_2))
    comparator = Comparator(pr1, pr2)
    print(f"\nSimilarities of Pull Request https://github.com/{repo}/pull/{pr_num_1} and Pull Request "
          f"https://github.com/{repo}/pull/{pr_num_2}")
    print(comparator)
    return comparator.compute_similarity_score()


def compute_duplications(file_path, threshold=0.5):
    duplicates = []
    not_duplicates = []
    with open(file_path, 'r') as source:
        for line in source:
            parts = line.split()
            repo = parts[0]
            pr_number_1 = parts[1]
            pr_number_2 = parts[2]
            if compare(repo, pr_number_1, pr_number_2) > threshold:
                duplicates.append(line)
            else:
                not_duplicates.append(line)
    print(f"\n\nDuplicated Assumed for file {file_path}:\n")
    for dup in duplicates:
        print(dup)
    print(f"\n\nNonDuplicated Assumed for file {file_path}:\n")
    for dup in not_duplicates:
        print(dup)
    return duplicates, not_duplicates


if __name__ == "__main__":
    compute_duplications('input/duplicated_pairs_1.txt', threshold=0.2)
    compute_duplications('input/nonduplicated_pairs_1.txt', threshold=0.2)
