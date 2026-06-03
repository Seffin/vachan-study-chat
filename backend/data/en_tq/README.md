<img src="https://cdn.door43.org/assets/uw-icons/logo-utq-256.png" alt="UTQ Logo" width="100"/>

# unfoldingWord® Translation Questions

This is the repository for the [unfoldingWord® Translation Questions (UTQ)](https://www.unfoldingword.org/utq/) resource.

## Description

unfoldingWord® Translation Questions are comprehension and theological questions for each chapter of the Bible. It enables translators and translation checkers to confirm that the intended meaning of their translations is clearly communicated to the speakers of that language.

## Downloading

If you want to download the UTQ to use, go here: [https://www.unfoldingword.org/utq/](https://www.unfoldingword.org/utq/). The UTQ are included in [tS](https://ufw.io/ts) and will soon be in [tC](https://ufw.io/tc).

## Improving the tQs

Please use the [issue queue](https://git.door43.org/unfoldingWord/en_tq/issues) to provide feedback or suggestions for improvement.

If you want to make your suggested changes then you may use the online editor to do so. See the [protected branch workflow](https://forum.ccbt.bible/t/protected-branch-workflow/76) document for step by step instructions.

## Editing the UTQ

To edit the UTQ files there are three options:

* Use LibreOffice (Recommended)
* Use a text editor on your computer
* Use the online web editor in DCS

Each of these options and their caveats are described below.

The first two options require you to clone the repository to your computer first. You may do this on the command line or using a program such as SmartGit. After making changes to the files you will need to commit and push your changes to the server and then create a Pull Request to merge them to the `master` branch.

Alternately, you may [download the master branch as a zip file](https://git.door43.org/unfoldingWord/en_tq/archive/master.zip) and extract that locally. After editing you would need to use the upload file feature in DCS to get your changes ready for a Pull Request.

### Editing in LibreOffice

This is the recommended way to edit the TSV files. You may [download LibreOffice](https://www.libreoffice.org/download/download/) for free.

After you have the file on your computer, you may open the respective TSV file with LibreOffice. Follow these notes on the Text Import Screen:

* Set “Separated by” to “Tab”
* Set “Text Delimiter” to blank, you will need to highlight the character and use backspace or delete to remove it

When you are done editing, click Save and then select “Use Text CSV Format” on the pop up dialogue. Note that even though it says CSV, it will use tab characters as the field separators.

**Note:** Other spreadsheet editors **should not** be used because they will add or remove quotation marks which will affect the notes negatively.

### Editing in a Text Editor

You may also use a regular text editor to make changes to the files.

**Note:** You must be careful not to delete or add any tab characters when editing with this method.

### Editing in DCS

If you only need to change a word or two, this may be the quickest way to make your change. See the [protected branch workflow](https://help.door43.org/en/knowledgebase/15-door43-content-service/docs/46-protected-branch-workflow) document for step by step instructions.

**Note:** You must be careful not to delete any tab characters when editing with this method.

## Structure

The UTQ are structured as TSV files to simplify importing and exporting into various formats for translation and presentation.

### TSV Format Overview

A Tab Separated Value (TSV) file is like a Comma Separated Value file except that the tab character is what divides the values instead of a comma. This makes it easier to include prose text in the files because many languages require the use of commas, single quotes, and double quotes in their sentences and paragraphs.

The UTQ are structured as one file per book of the bible and encoded in TSV format, for example, `tq_GEN.tsv`. The columns are `Reference`, `ID`, `Tags`, `Quote`, `Occurrence`, `Question`, and `Response`.

### UTQ TSV Column Description

The following lists each column with a brief description and example.

* `Reference`: Chapter number (e.g. `1`) then colon then verse number (e.g. `3`) or `intro`
* `ID`: Four character **alphanumeric** string unique *within* the verse for the resource (e.g. `swi9`)
  * This will be helpful in identifing which notes are translations of the original English tQs and which notes have been added by GLs.
  * The Universal ID (UID) of a note is the combination of the `Book`, `Chapter`, `Verse`, and `ID` fields. For example, `tit/1/3/swi9`.
    * This is a useful way to unambiguously refer to notes.
    * An [RC link](https://resource-container.readthedocs.io/en/latest/linking.html) can resolve to a specific note like this: `rc://en/tq/help/tit/01/01/swi9`.
* `Tags`: not currently used for Translation Questions
* `Quote`: currently only used for OBS Translation Questions
* `Occurrence`: Specifies which occurrence in the original language text the entry applies to.
  * `-1`: entry applies to every occurrence of Quote in the verse
  * `0`: entry does not occur in original language (for example, “Connecting Statement:”)
  * `1`: entry applies to first occurrence of Quote only
  * `2`: entry applies to second occurrence of Quote only
  * etc.
* `Question`: The character Markdown formatted question.
* `Response`: Optional character Markdown formatted response.
  * The Question and Response text should only be characters Markdown formatted, which means the following are also acceptable:
    * Plaintext—if you have no need for extra markup, just use plain text in this column
    * HTML—if you prefer to use inline HTML for markup, that works because it is supported in Markdown
    * No paragraph Markdown formats

## GL Translators

### UTQ Translation Philosophy

To learn the philosophy of how to translate the UTQs please see the [Translate the unfoldingWord® Translation Questions](https://gl-manual.readthedocs.io/en/latest/gl_translation.html#translating-translationquestions) article in the [Gateway Language Manual](https://gl-manual.readthedocs.io/).

If you are translating online, please fork the [Door43-Catalog/en_tq](https://git.door43.org/Door43-Catalog/en_tq) repository, following this workflow: [Translate Content Online](https://forum.ccbt.bible/t/translate-content-online/75).

## License

See the [LICENSE](https://git.door43.org/unfoldingWord/en_tq/src/branch/master/LICENSE.md) file for licensing information.
