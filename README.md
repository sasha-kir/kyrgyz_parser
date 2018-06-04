#  Kyrgyz Parser Bot

This is a telegram bot that can:
+ analyze Kyrgyz morphology
+ look up stems in a Kyrgyz-Russian [online dictionary](http://el-sozduk.kg/ru/)

Morphological analyzer is based on the [transducer](https://github.com/apertium/apertium-kir/) developed as part of the open-source platform Apertium.

## Contents
File     | What it does   
--------------|-------------------------
**parser_bot.py**    | telegram bot for morphological analysis
**find_mistakes.py**     | test transducer output quality

## Installation

You will need to install [**Apertium**](http://wiki.apertium.org/wiki/Installation).

To make changes to the transducer files:
1. clone the [**apertium-kir**](https://github.com/apertium/apertium-kir/) repo
2. change the .lexc, .twol and .rlx files
3. complile:

    ```
    $ ./autogen.sh 
    $ make
    ```
4. place new **kir.automorf.bin** and **kir.rlx.bin** files in the *transducer* directory

## Changes to Apertium transducer
- fixed issue with **Й** and **й**
- added support of some non-dictionary stems (nouns and verbs)

    example:
    ```
    чокойлорду
    чокой<n><unk><pl><acc>
    ```
