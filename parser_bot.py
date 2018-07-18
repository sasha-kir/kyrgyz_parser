import subprocess
import os
import urllib.request as urr
import urllib.error as ure
import re
from string import punctuation
from bs4 import BeautifulSoup
from transliterate import translit
from alphabet_detector import AlphabetDetector
from telegram import ParseMode
from telegram.ext import (Updater, CommandHandler, MessageHandler, ConversationHandler, RegexHandler, Filters)
import logging


logging.basicConfig(format='%(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO,
                    filename='bot.log'
                    )

PARSE, PARSE_TEXT = 0, 1

TOKEN = os.environ["KYRGYZ_BOT"]
PORT = int(os.environ.get("PORT", "5000"))

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


def run_apertium_tagger(input, mode="word"):
    working_directory = os.path.dirname(os.path.abspath(__file__))

    echo_word = "echo '" + input + "'"
    cmd = echo_word + "| " \
          "lt-proc -w transducer/kir.automorf.bin | " \
          "cg-proc -1 transducer/kir.rlx.bin"
    ps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=working_directory)
    output = ps.communicate()[0]
    result = output.decode("utf-8")
    if mode == "word":
        res_match = re.match(r"(?:\^.+\/)\*?((.+?)(<.+>)?)\$", result)
        if not res_match[3] and ("Й" in input or "й" in input):
            input = input.replace("Й", "J")
            input = input.replace("й", "j", 1)
            res_match = run_apertium_tagger(input)
            return res_match
        else:
            return res_match
    else:
        words_split = re.split(r'[\^\$]', result)
        result_list = list(filter(lambda x: (x.strip() not in punctuation), words_split))
        word_match_list = []
        for word in result_list:
            word_match = re.match(r"(?:.+?)\/\*?([А-ЯӨҮҢJjа-яёөүң\s]+)(<.+>)?", word)
            if word_match:
                if not word_match[2] and ("Й" in word_match[1] or "й" in word_match[1]):
                    word_new = str(word_match[1]).replace("Й", "J")
                    word_new = word_new.replace("й", "j", 1)
                    word_match = run_apertium_tagger(word_new, mode="text")
                    word_match = word_match[0]
            word_match_list.append(word_match)
        return word_match_list


def check_link(source):
    request = urr.Request(source, headers=HEADERS)
    try:
        response = urr.urlopen(request)
        contents = response.read().decode("utf8")
        return contents
    except ure.HTTPError:
        return False


def get_dict_entry(bot, update, contents, stem):
    soup = BeautifulSoup(contents, "html.parser")
    dict_link = "http://el-sozduk.kg/ru/" + stem
    russian_available = soup.find(id="words").find("a", href="/dictionaries/show2/")
    if russian_available:
        update.message.reply_text(dict_link)
        update.message.reply_text("*Russian translation found*", parse_mode=ParseMode.MARKDOWN)
        html_entry_text = soup.find(id="words").find(id=re.compile("^DicBody[0-9]+")).find("table").contents[3].contents[0].get_text()
        for line in re.split("[;]", html_entry_text):
            update.message.reply_text(line.strip())
        update.message.reply_text("*-----*", parse_mode=ParseMode.MARKDOWN)
    else:
        stem += "-"
        contents = check_link(dict_link + "-")
        if contents:
            get_dict_entry(bot, update, contents, stem)
        else:
            update.message.reply_text("*No Russian translation found*", parse_mode=ParseMode.MARKDOWN)


def greet_user(bot, update):
    user = update.message.from_user
    update.message.reply_text('Hi {}! Enter words in Kyrgyz and I will help you with parsing. \n'
                              'To enter text mode, press /text_mode \n'
                              'To exit, press /cancel at any time'.format(user.first_name))
    return PARSE


def word_error(bot, update):
    update.message.reply_text("You entered more than 1 word, which is not a supported input format in current mode. "
                              "To switch to text mode, press /text_mode or enter next word to continue.")


def parse_input(bot, update, user_data):
    input = update.message.text
    ad = AlphabetDetector()
    if ad.is_latin(input):
        update.message.reply_text("Right now only cyrillic characters are supported :( \n"
                                  "Enter a Kyrgyz word:")
    else:
        result = run_apertium_tagger(input)
        if user_data.setdefault("stem", []):
            user_data["stem"] = []
        result_2 = str(result[2]).replace("J", "Й")
        result_2 = result_2.replace("j", "й")
        user_data['stem'].append(result_2.lower())

        if result[3] is not None:
            user_data['stem'].append(1)
            user_data['stem'].append(result[3])
            reply = result_2 + "*" + result[3] + "*"
            update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
            update.message.reply_text("Look up stem in the dictionary? \n"
                                      "Press /find or enter next word to continue.")
        else:
            user_data['stem'].append(0)
            update.message.reply_text(result_2)
            update.message.reply_text("Parsing didn't work :( \n"
                                      "Look up stem in the dictionary? \n"
                                      "Press /find or enter next word to continue.")


def parse_text(bot, update):
    input = update.message.text
    ad = AlphabetDetector()
    if ad.is_latin(input):
        update.message.reply_text("Right now only cyrillic characters are supported :( \n"
                                  "Enter a Kyrgyz text:")
    else:
        match_list = run_apertium_tagger(input, mode="text")
        output_list, error_list = [], []
        for word_match in match_list:
            if not word_match:
                continue
            else:
                word_match_1 = str(word_match[1]).replace("J", "Й")
                word_match_1 = word_match_1.replace("j", "й")

                if word_match[2] is not None:
                    output_list.append(word_match_1 + "*" + word_match[2] + "*")
                else:
                    output_list.append("_" + word_match_1 + "_")
                    error_list.append(word_match_1)

        update.message.reply_text(" ".join(output_list), parse_mode=ParseMode.MARKDOWN)
        if error_list:
            update.message.reply_text("⚠️ These words were not recognized by the parser ⚠️")
            for word in error_list:
                update.message.reply_text(word)
        update.message.reply_text("*-----*", parse_mode=ParseMode.MARKDOWN)


def find_in_dict(bot, update, user_data):
    stem = user_data['stem']
    user_data.clear()

    stem_translit = translit(stem[0], 'ru', reversed=True)
    substrings = sorted(KG_LETTERS, key=len, reverse=True)
    regex = re.compile('|'.join(map(re.escape, substrings)))
    stem_final = regex.sub(lambda match: KG_LETTERS[match.group(0)], stem_translit)

    if stem[1] == 0:
        while len(stem_final) > 2:
            stem_final = stem_final[:-1]
            dict_link = "http://el-sozduk.kg/ru/" + stem_final
            contents = check_link(dict_link)
            if contents:
                get_dict_entry(bot, update, contents, stem_final)
                break
        else:
            update.message.reply_text("Seems like there is no such stem in the dictionary :(")

    else:
        dict_link = "http://el-sozduk.kg/ru/" + stem_final
        contents = check_link(dict_link)
        if contents:
            get_dict_entry(bot, update, contents, stem_final)
        else:
            update.message.reply_text("Seems like there is no such stem in the dictionary :(")


def switch_to_text(bot, update):
    update.message.reply_text("You entered text mode. \n"
                              "To return to word-by-word parsing, press /word_mode")
    return PARSE_TEXT


def switch_to_words(bot, update):
    update.message.reply_text("You entered word-by-word parsing mode. Enter a Kyrgyz word:")
    return PARSE


def cancel(bot, update):
    update.message.reply_text('Thank you for using this service. Goodbye!')
    return ConversationHandler.END


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


if __name__ == "__main__":
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    parse_kyrgyz = ConversationHandler(
        entry_points=[CommandHandler("start", greet_user)],

        states={
            PARSE: [RegexHandler("^[^\s\/]+$", parse_input, pass_user_data=True),
                    RegexHandler("^.+\s.+$", word_error),
                    CommandHandler("find", find_in_dict, pass_user_data=True),
                    CommandHandler("text_mode", switch_to_text)],
            PARSE_TEXT: [MessageHandler(Filters.text, parse_text),
                         CommandHandler("word_mode", switch_to_words)]
        },

        fallbacks=[CommandHandler("cancel", cancel)]
    )

    dp.add_handler(parse_kyrgyz)

    dp.add_error_handler(error)

    updater.start_webhook(listen="0.0.0.0",
                          port=PORT,
                          url_path=TOKEN)

    updater.bot.setWebhook("https://kyrgyz-parser-bot.herokuapp.com/" + TOKEN)

    updater.idle()