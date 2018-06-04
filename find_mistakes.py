import subprocess
import os
import re
from string import punctuation
from tqdm import tqdm
import urllib.request as urr
import urllib.error as ure
from transliterate import translit
from collections import defaultdict

HEADERS = {'User-Agent':
           'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) '
           'AppleWebKit/537.36 (KHTML, like Gecko) '
           'Chrome/35.0.1916.47 '
           'Safari/537.36'}

KG_LETTERS = {"ң": "n",
              "ү": "u",
              "ө": "o",
              "j": "y",
              "'": ""}


def run_apertium_tagger(input, mode="text"):
    """
    Analyse input text
    """
    working_directory = os.path.dirname(os.path.abspath(__file__))

    if mode != "text":
        echo_word = "echo '" + input + "'"
        cmd = echo_word + "| " \
              "lt-proc -w transducer/kir.automorf.bin | " \
              "cg-proc -1 transducer/kir.rlx.bin"
    else:
        print("Processing text...")
        cmd = "lt-proc -w transducer/kir.automorf.bin < " \
              + working_directory + "/" + input + " | " \
              "cg-proc -1 transducer/kir.rlx.bin"

    ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=working_directory)
    output = ps.communicate()[0]
    result = output.decode("utf-8")

    words_split = re.split(r'[\^\$]', result)
    result_list = list(filter(lambda x: (x.strip() not in punctuation), words_split))
    word_match_list = []
    for word in tqdm(result_list):
        word_match = re.match(r"(?:.+?)\/\*?([А-ЯӨҮҢJjа-яёөүң\s]+)(<.+>)?", word)
        if word_match:
            if not word_match[2] and ("Й" in word_match[1] or "й" in word_match[1]):
                word_new = str(word_match[1]).replace("Й", "J")
                word_new = word_new.replace("й", "j", 1)
                word_match = run_apertium_tagger(word_new, mode="word")[0]
        word_match_list.append(word_match)
    return word_match_list


def read_analyzed(text_input):
    """
    Convert results into a list
    """
    word_results = []
    match_list = run_apertium_tagger(text_input)
    for word_match in match_list:
        if not word_match:
            continue
        else:
            word_match_0 = str(word_match[0]).replace("J", "Й")
            word_match_0 = word_match_0.replace("j", "й")
            word_results.append(re.split(r'[/]', word_match_0))
    return word_results


def check_link(source):
    """
    Check for 404 error
    """
    request = urr.Request(source, headers=HEADERS)
    try:
        response = urr.urlopen(request)
        return True
    except ure.HTTPError:
        return False


def check_dict(unk_list):
    """
    Check whether dictionary entry for stem exists and count false stems
    """
    stems_translit = defaultdict(str)
    stems, false_stems = [], []
    false_count = 0

    for unk_word in unk_list:
        stem_match = re.match(r'([а-яёөүң\s]+)(<.+>)?', unk_word)
        stem = stem_match[1]
        stems.append(stem)

        stem_translit = translit(stem, 'ru', reversed=True)
        substrings = sorted(KG_LETTERS, key=len, reverse=True)
        regex = re.compile('|'.join(map(re.escape, substrings)))
        stem_final = regex.sub(lambda match: KG_LETTERS[match.group(0)], stem_translit)
        stems_translit[stem] = stem_final

    print("\n\nChecking for false stems...")
    for stem, lat_stem in tqdm(stems_translit.items()):
        dict_link = "http://el-sozduk.kg/ru/" + lat_stem
        stem_exists = check_link(dict_link)
        if not stem_exists:
            false_stems.append(stem)

    for stem in stems:
        if stem in false_stems:
            false_count += 1

    print("False stems found: {}".format(len(false_stems)))
    print("False stems total: {}".format(false_count))

    return false_count


if __name__ == "__main__":

    text_input = "test_corpus.txt"

    word_results = read_analyzed(text_input)

    stop_words = []
    with open("stop_words.txt", "r", encoding="utf-8") as stop_list:
        for word in stop_list:
            stop_words.append(word.strip("\n"))

    total_count, unk_tag_count, no_tags_count = 0, 0, 0
    unk_list = []

    for word in word_results:
        if any(x in word[1].lower() for x in stop_words):
            continue
        else:
            total_count += 1
            if "unk" in word[1]:
                unk_tag_count += 1
                unk_list.append(word[1].lower())
            if "*" in word[1]:
                no_tags_count += 1

    false_count = check_dict(unk_list)

    mistakes_before = unk_tag_count + no_tags_count
    mistakes_after = false_count + no_tags_count

    print("total: {}".format(total_count))
    print("before changes: {} ({}%)".format(mistakes_before, (mistakes_before / total_count)*100))
    print("after changes: {} ({}%)".format(mistakes_after, (mistakes_after / total_count)*100))
