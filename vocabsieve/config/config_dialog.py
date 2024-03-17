from PyQt5.QtWidgets import (QDialog, QStatusBar, QCheckBox, QComboBox, QLineEdit,
                             QSpinBox, QPushButton, QSlider, QLabel, QHBoxLayout,
                             QWidget, QTabWidget, QMessageBox, QColorDialog, QListWidget,
                             QFormLayout, QGridLayout, QVBoxLayout
                             )
from PyQt5.QtGui import QImageWriter
from PyQt5.QtCore import Qt, pyqtSlot
import platform
import qdarktheme
from shutil import rmtree

from ..fieldmatcher import FieldMatcher
from ..ui import SourceGroupWidget, AllSourcesWidget
from ..models import DisplayMode, FreqDisplayMode, LemmaPolicy
from loguru import logger
from ..tools import (addDefaultModel, getVersion, findNotes,
                     guiBrowse, getDeckList,
                     getNoteTypes, getFields
                     )
from .general_tab import GeneralTab
from .source_tab import SourceTab
from .processing_tab import ProcessingTab
from ..global_names import settings

import os


class ConfigDialog(QDialog):
    def __init__(self, parent, ):
        super().__init__(parent)
        logger.debug("Initializing settings dialog")
        user_note_type = settings.value("note_type")
        self.parent = parent
        self.resize(700, 500)
        self.setWindowTitle("Configure VocabSieve")
        logger.debug("Initializing widgets for settings dialog")
        self.initWidgets()
        self.initTabs()
        logger.debug("Setting up widgets")
        self.setupWidgets()
        logger.debug("Setting up autosave")
        self.setupAutosave()
        logger.debug("Setting up processing")
        logger.debug("Fetching matched cards from AnkiConnect")
        self.getMatchedCards()
        logger.debug("Got matched cards")

        if not user_note_type and not settings.value("internal/added_default_note_type"):
            try:
                self.onDefaultNoteType()
                settings.setValue("internal/added_default_note_type", True)
            except Exception:
                pass

    def initWidgets(self):
        self.status_bar = QStatusBar()
        self.allow_editing = QCheckBox(
            "Allow directly editing definition fields")
        self.primary = QCheckBox("*Use primary selection")
        self.register_config_handler(self.allow_editing, "allow_editing", True)
        self.capitalize_first_letter = QCheckBox(
            "Capitalize first letter of sentence")
        self.capitalize_first_letter.setToolTip(
            "Capitalize the first letter of clipboard's content before pasting into the sentence field. Does not affect dictionary lookups.")
        
        self.deck_name = QComboBox()
        self.tags = QLineEdit()
        self.note_type = QComboBox()
        self.sentence_field = QComboBox()
        self.book_path = QLineEdit()

        self.word_field = QComboBox()
        self.frequency_field = QComboBox()
        self.definition1_field = QComboBox()
        self.definition2_field = QComboBox()
        self.pronunciation_field = QComboBox()

        #self.orientation = QComboBox()
        self.text_scale = QSlider(Qt.Horizontal)

        self.text_scale.setTickPosition(QSlider.TicksBelow)
        self.text_scale.setTickInterval(10)
        self.text_scale.setSingleStep(5)
        self.text_scale.setValue(100)
        self.text_scale.setMinimum(50)
        self.text_scale.setMaximum(250)
        self.text_scale_label = QLabel("1.00x")
        self.text_scale_box = QWidget()
        self.text_scale_box_layout = QHBoxLayout()
        self.text_scale_box.setLayout(self.text_scale_box_layout)
        self.text_scale_box_layout.addWidget(self.text_scale)
        self.text_scale_box_layout.addWidget(self.text_scale_label)

        #self.orientation.addItems(["Vertical", "Horizontal"])
        self.gtrans_api = QLineEdit()
        self.anki_api = QLineEdit()

        #self.api_enabled = QCheckBox("Enable VocabSieve local API")
        #self.api_host = QLineEdit()
        #self.api_port = QSpinBox()
        #self.api_port.setMinimum(1024)
        #self.api_port.setMaximum(49151)

        self.reader_enabled = QCheckBox("Enable VocabSieve Web Reader")
        self.reader_host = QLineEdit()
        self.reader_port = QSpinBox()
        self.reader_port.setMinimum(1024)
        self.reader_port.setMaximum(49151)

        self.reset_button = QPushButton("Reset settings")
        self.reset_button.setStyleSheet('QPushButton {color: red;}')
        self.nuke_button = QPushButton("Delete data")
        self.nuke_button.setStyleSheet('QPushButton {color: red;}')

        self.enable_anki = QCheckBox("Enable sending notes to Anki")
        self.check_updates = QCheckBox("Check for updates")

        self.img_format = QComboBox()
        self.img_format.addItems(
            ['png', 'jpg', 'gif', 'bmp']
        )
        supported_img_formats = list(map(lambda s: bytes(s).decode(), QImageWriter.supportedImageFormats()))
        # WebP requires a plugin, which is commonly but not always installed
        if 'webp' in supported_img_formats:
            self.img_format.addItem('webp')

        self.img_quality = QSpinBox()
        self.img_quality.setMinimum(-1)
        self.img_quality.setMaximum(100)

        self.image_field = QComboBox()

        self.freq_display_mode = QComboBox()
        self.freq_display_mode.addItems([
            FreqDisplayMode.stars,
            FreqDisplayMode.rank
        ])

        self.anki_query_mature = QLineEdit()
        self.mature_count_label = QLabel("")
        self.anki_query_young = QLineEdit()
        self.young_count_label = QLabel("")

        self.default_notetype_button = QPushButton(
            "Use default note type ('vocabsieve-notes', will be created if it does not exist)")
        self.default_notetype_button.setToolTip(
            "This will use the default note type provided by VocabSieve. It will be created if it does not exist.")
        self.default_notetype_button.clicked.connect(self.onDefaultNoteType)

        self.preview_young_button = QPushButton("Preview in Anki Browser")
        self.preview_mature_button = QPushButton("Preview in Anki Browser")

        self.known_data_lifetime = QSpinBox()
        self.known_data_lifetime.setSuffix(" seconds")
        self.known_data_lifetime.setMinimum(0)
        self.known_data_lifetime.setMaximum(1000000)
        self.known_threshold = QSpinBox()
        self.known_threshold.setMinimum(1)
        self.known_threshold.setMaximum(1000)
        self.known_threshold_cognate = QSpinBox()
        self.known_threshold_cognate.setMinimum(1)
        self.known_threshold_cognate.setMaximum(1000)
        self.w_seen = QSpinBox()
        self.w_seen.setMinimum(0)
        self.w_seen.setMaximum(1000)
        self.w_lookup = QSpinBox()
        self.w_lookup.setMinimum(0)
        self.w_lookup.setMaximum(1000)
        self.w_anki_ctx = QSpinBox()
        self.w_anki_ctx.setMinimum(0)
        self.w_anki_ctx.setMaximum(1000)
        self.w_anki_word = QSpinBox()
        self.w_anki_word.setMinimum(0)
        self.w_anki_word.setMaximum(1000)
        self.w_anki_ctx_y = QSpinBox()
        self.w_anki_ctx_y.setMinimum(0)
        self.w_anki_ctx_y.setMaximum(1000)
        self.w_anki_word_y = QSpinBox()
        self.w_anki_word_y.setMinimum(0)
        self.w_anki_word_y.setMaximum(1000)

        self.theme = QComboBox()
        self.theme.addItems(qdarktheme.get_themes())
        self.theme.addItem("system")

        self.accent_color = QPushButton()
        self.accent_color.setText(settings.value("accent_color", "default"))
        self.accent_color.setToolTip("Hex color code (e.g. #ff0000 for red)")
        self.accent_color.clicked.connect(self.save_accent_color)

        self.known_langs = QLineEdit("en")
        self.known_langs.setToolTip(
            "Comma-separated list of languages that you know. These will be used to determine whether a word is cognate or not.")

        self.open_fieldmatcher = QPushButton("Match fields (required for using Anki data)")

        

    def initTabs(self):
        self.tabs = QTabWidget()
        # block signals
        self.tab_g = GeneralTab()  # General
        self.tab_s = SourceTab()  # Sources
        self.tab_g.sources_reloaded_signal.connect(self.tab_s.reloadSources)
        self.tab_s.sg2_visibility_changed.connect(self.changeMainLayout)
        self.tab_p = ProcessingTab()  # Processing
        self.tab_g.sources_reloaded_signal.connect(self.tab_p.setupSelector)
        self.tab_a = QWidget()  # Anki
        self.tab_a_layout = QFormLayout(self.tab_a)
        self.tab_n = QWidget()  # Network
        self.tab_n_layout = QFormLayout(self.tab_n)
        self.tab_i = QWidget()  # Interface
        self.tab_i_layout = QFormLayout(self.tab_i)
        self.tab_m = QWidget()  # Miscellaneous
        self.tab_m_layout = QFormLayout(self.tab_m)
        self.tab_t = QWidget()  # Tracking
        self.tab_t_layout = QFormLayout(self.tab_t)
        self.tab_g.load_dictionaries()

        self.tabs.resize(400, 400)

        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self.tabs)
        self._layout.addWidget(self.status_bar)

        self.tabs.addTab(self.tab_g, "General")
        self.tabs.addTab(self.tab_s, "Sources")
        self.tabs.addTab(self.tab_p, "Processing")
        self.tabs.addTab(self.tab_a, "Anki")
        self.tabs.addTab(self.tab_n, "Network")
        self.tabs.addTab(self.tab_t, "Tracking")
        self.tabs.addTab(self.tab_i, "Interface")
        self.tabs.addTab(self.tab_m, "Misc")

    def save_accent_color(self):
        color = QColorDialog.getColor()
        if color.isValid() and settings.value("theme") != "system":
            settings.setValue("accent_color", color.name())
            self.accent_color.setText(color.name())
            qdarktheme.setup_theme(
                settings.value("theme", "dark"),
                custom_colors={"primary": color.name()}
            )

    def reset_settings(self):
        answer = QMessageBox.question(
            self,
            "Confirm Reset<",
            "<h1>Danger!</h1>"
            "Are you sure you want to reset all settings? "
            "This action cannot be undone. "
            "This will also close the configuration window.",
            defaultButton=QMessageBox.StandardButton.No
        )
        if answer == QMessageBox.Yes:
            settings.clear()
            self.close()

    def nuke_profile(self):
        datapath = self.parent.datapath
        answer = QMessageBox.question(
            self,
            "Confirm Reset",
            "<h1>Danger!</h1>"
            "Are you sure you want to delete all user data? "
            "The following directory will be deleted:<br>" + datapath
            + "<br>This action cannot be undone. "
            "This will also close the program.",
            defaultButton=QMessageBox.StandardButton.No
        )
        if answer == QMessageBox.Yes:
            settings.clear()
            rmtree(datapath)
            os.mkdir(datapath)
            self.parent.close()

    def onDefaultNoteType(self):
        try:
            addDefaultModel(settings.value("anki_api", 'http://127.0.0.1:8765'))
        except Exception:
            pass
        self.loadDecks()
        self.loadFields()
        self.note_type.setCurrentText("vocabsieve-notes")
        self.sentence_field.setCurrentText("Sentence")
        self.word_field.setCurrentText("Word")
        self.definition1_field.setCurrentText("Definition")
        self.definition2_field.setCurrentText("Definition#2")
        self.pronunciation_field.setCurrentText("Pronunciation")
        self.image_field.setCurrentText("Image")

    def setupWidgets(self):

        self.tab_a_layout.addRow(QLabel("<h3>Anki settings</h3>"))
        self.tab_a_layout.addRow(self.enable_anki)
        self.tab_a_layout.addRow(
            QLabel("<i>◊ If disabled, notes will not be sent to Anki, but only stored in a local database.</i>")
        )
        self.tab_a_layout.addRow(QLabel("<hr>"))
        self.tab_a_layout.addRow(QLabel('AnkiConnect API'), self.anki_api)
        self.tab_a_layout.addRow(QLabel("Deck name"), self.deck_name)
        self.tab_a_layout.addRow(QLabel('Default tags'), self.tags)
        self.tab_a_layout.addRow(QLabel("<hr>"))
        self.tab_a_layout.addRow(self.default_notetype_button)
        self.tab_a_layout.addRow(QLabel("Note type"), self.note_type)
        self.tab_a_layout.addRow(
            QLabel('Field name for "Sentence"'),
            self.sentence_field)
        self.tab_a_layout.addRow(
            QLabel('Field name for "Word"'),
            self.word_field)
        #self.tab_a_layout.addRow(
        #    QLabel('Field name for "Frequency Stars"'),
        #    self.frequency_field)
        self.tab_a_layout.addRow(
            QLabel('Field name for "Definition"'),
            self.definition1_field)
        self.tab_a_layout.addRow(
            QLabel('Field name for "Definition#2"'),
            self.definition2_field)
        self.tab_a_layout.addRow(
            QLabel('Field name for "Pronunciation"'),
            self.pronunciation_field)
        self.tab_a_layout.addRow(
            QLabel('Field name for "Image"'),
            self.image_field)

        self.tab_n_layout.addRow(QLabel(
            '<h3>Network settings</h3>'
            '◊ All settings on this tab require a restart to take effect.'
            '<br>◊ Most users should not need to change these settings.</i>'
        ))
        self.tab_n_layout.addRow(self.check_updates)
        #self.tab_n_layout.addRow(QLabel("<h4>Local API</h4>"))
        #self.tab_n_layout.addRow(self.api_enabled)
        #self.tab_n_layout.addRow(QLabel("API host"), self.api_host)
        #self.tab_n_layout.addRow(QLabel("API port"), self.api_port)
        self.tab_n_layout.addRow(QLabel("<h4>Web Reader</h4>"))
        self.tab_n_layout.addRow(self.reader_enabled)
        self.tab_n_layout.addRow(QLabel("Web reader host"), self.reader_host)
        self.tab_n_layout.addRow(QLabel("Web reader port"), self.reader_port)
        self.tab_n_layout.addRow(
            QLabel("Google Translate API"),
            self.gtrans_api)

        self.tab_i_layout.addRow(
            QLabel("<h3>Interface settings</h3>")
        )
        self.tab_i_layout.addRow(
            QLabel("<h4>Settings marked * require a restart to take effect.</h4>"))
        if platform.system() == "Linux":
            # Primary selection is only available on Linux
            self.tab_i_layout.addRow(self.primary)
        self.tab_i_layout.addRow("Theme", self.theme)
        self.tab_i_layout.addRow(QLabel('<i>◊ Changing to "system" requires a restart.</i>'))
        self.tab_i_layout.addRow("Accent color", self.accent_color)
        self.tab_i_layout.addRow(self.allow_editing)
        self.tab_i_layout.addRow(QLabel("Frequency display mode"), self.freq_display_mode)
        #self.tab_i_layout.addRow(QLabel("*Interface layout orientation"), self.orientation)
        self.tab_i_layout.addRow(QLabel("*Text scale"), self.text_scale_box)

        self.text_scale.valueChanged.connect(
            lambda _: self.text_scale_label.setText(
                format(
                    self.text_scale.value() / 100,
                    "1.2f") + "x"))

        self.tab_m_layout.addRow(self.capitalize_first_letter)
        self.tab_m_layout.addRow(QLabel("<h3>Images</h3>"))
        self.tab_m_layout.addRow(QLabel("Image format"), self.img_format)
        self.tab_m_layout.addRow(QLabel("<i>◊ WebP, JPG, GIF are lossy, which create smaller files.</i>"))
        self.tab_m_layout.addRow(QLabel("Image quality"), self.img_quality)
        self.tab_m_layout.addRow(QLabel("<i>◊ Between 0 and 100. -1 uses the default value from Qt.</i>"))
        self.tab_m_layout.addRow(QLabel("<h3>Reset</h3>"))
        self.tab_m_layout.addRow(QLabel("Your data will be lost forever! There is NO cloud backup."))
        self.tab_m_layout.addRow(QLabel("<strong>Reset all settings to defaults</strong>"), self.reset_button)
        self.tab_m_layout.addRow(QLabel("<strong>Delete all user data</strong>"), self.nuke_button)

        self.tab_t_layout.addRow(QLabel("<h3>Anki tracking</h3>"))
        self.tab_t_layout.addRow(QLabel("Use the Anki Card Browser to make a query string. "
                                        "<br>Mature cards are excluded from the list of young cards automatically"))

        self.tab_t_layout.addRow(QLabel("Query string for 'mature' cards"), self.anki_query_mature)
        self.tab_t_layout.addRow(self.mature_count_label, self.preview_mature_button)
        self.tab_t_layout.addRow(QLabel("Query string for 'young' cards"), self.anki_query_young)
        self.tab_t_layout.addRow(self.young_count_label, self.preview_young_button)
        self.tab_t_layout.addRow(self.open_fieldmatcher)
        self.tab_t_layout.addRow(QLabel("<h3>Word scoring</h3>"))
        self.tab_t_layout.addRow(QLabel("Known languages (use commas)"), self.known_langs)
        self.tab_t_layout.addRow(QLabel("Known data lifetime"), self.known_data_lifetime)
        self.tab_t_layout.addRow(QLabel("Known threshold score"), self.known_threshold)
        self.tab_t_layout.addRow(QLabel("Known threshold score (cognate)"), self.known_threshold_cognate)
        self.tab_t_layout.addRow(QLabel("Score: seen"), self.w_seen)
        self.tab_t_layout.addRow(QLabel("Score: lookup (max 1 per day)"), self.w_lookup)
        self.tab_t_layout.addRow(QLabel("Score: mature Anki target word"), self.w_anki_word)
        self.tab_t_layout.addRow(QLabel("Score: mature Anki card context"), self.w_anki_ctx)
        self.tab_t_layout.addRow(QLabel("Score: young Anki target word"), self.w_anki_word_y)
        self.tab_t_layout.addRow(QLabel("Score: young Anki card context"), self.w_anki_ctx_y)

        self.reset_button.clicked.connect(self.reset_settings)
        self.nuke_button.clicked.connect(self.nuke_profile)

        

        

        

    def getMatchedCards(self):
        if settings.value("enable_anki", True):
            try:
                _ = getVersion(api := settings.value('anki_api', 'http://127.0.0.1:8765'))
                query_mature = self.anki_query_mature.text()
                mature_notes = findNotes(api, query_mature)
                self.mature_count_label.setText(f"Matched {str(len(mature_notes))} notes")
                query_young = self.anki_query_young.text()
                young_notes = findNotes(api, query_young)
                young_notes = [note for note in young_notes if note not in mature_notes]
                self.young_count_label.setText(f"Matched {str(len(young_notes))} notes")
            except Exception:
                pass


    def setupAutosave(self):
        if settings.value("config_ver") is None \
                and settings.value("target_language") is not None:
            # if old config is copied to new location, nuke it
            settings.clear()
        settings.setValue("config_ver", 1)
        self.register_config_handler(
            self.anki_api, 'anki_api', 'http://127.0.0.1:8765')

        self.register_config_handler(self.check_updates, 'check_updates', False, True)

        self.register_config_handler(self.enable_anki, 'enable_anki', True)
        self.enable_anki.clicked.connect(self.toggle_anki_settings)
        self.toggle_anki_settings(self.enable_anki.isChecked())
        api = self.anki_api.text()
        try:
            _ = getVersion(api)
        except Exception:
            self.toggle_anki_settings(False)
        else:
            self.loadDecks()
            self.loadFields()
            self.register_config_handler(
                self.deck_name, 'deck_name', 'Default')
            self.register_config_handler(self.tags, 'tags', 'vocabsieve')
            self.register_config_handler(self.note_type, 'note_type', 'vocabsieve-notes')
            self.register_config_handler(
                self.sentence_field, 'sentence_field', 'Sentence')
            self.register_config_handler(self.word_field, 'word_field', 'Word')
            self.register_config_handler(self.frequency_field, 'frequency_field', 'Frequency Stars')
            self.register_config_handler(
                self.definition1_field, 'definition1_field', 'Definition')
            self.register_config_handler(
                self.definition2_field,
                'definition2_field',
                '<disabled>')
            self.register_config_handler(
                self.pronunciation_field,
                'pronunciation_field',
                "<disabled>")
            self.register_config_handler(self.image_field, 'image_field', "<disabled>")

        
        self.note_type.currentTextChanged.connect(self.loadFields)
        #self.api_enabled.clicked.connect(self.setAvailable)
        self.reader_enabled.clicked.connect(self.setAvailable)

        #self.register_config_handler(self.api_enabled, 'api_enabled', True)
        #self.register_config_handler(self.api_host, 'api_host', '127.0.0.1')
        #self.register_config_handler(self.api_port, 'api_port', 39284)
        self.register_config_handler(
            self.reader_enabled, 'reader_enabled', True)
        self.register_config_handler(
            self.reader_host, 'reader_host', '127.0.0.1')
        self.register_config_handler(self.reader_port, 'reader_port', 39285)
        self.register_config_handler(
            self.gtrans_api,
            'gtrans_api',
            'https://lingva.lunar.icu')

        self.register_config_handler(self.freq_display_mode, "freq_display", "Stars (like Migaku)")
        self.register_config_handler(self.allow_editing, 'allow_editing', True)
        self.register_config_handler(self.primary, 'primary', False)
        #self.register_config_handler(
        #    self.orientation, 'orientation', 'Vertical')
        self.register_config_handler(self.text_scale, 'text_scale', '100')

        self.register_config_handler(self.capitalize_first_letter, 'capitalize_first_letter', False)
        self.register_config_handler(self.img_format, 'img_format', 'jpg')
        self.register_config_handler(self.img_quality, 'img_quality', -1)

        self.register_config_handler(self.anki_query_mature, 'tracking/anki_query_mature', "prop:ivl>=14")
        self.register_config_handler(self.anki_query_young, 'tracking/anki_query_young', "prop:ivl<14 is:review")
        self.register_config_handler(self.known_threshold, 'tracking/known_threshold', 100)
        self.register_config_handler(self.known_threshold_cognate, 'tracking/known_threshold_cognate', 25)
        self.register_config_handler(self.known_langs, 'tracking/known_langs', 'en')
        self.register_config_handler(self.w_seen, 'tracking/w_seen', 8)
        self.register_config_handler(self.w_lookup, 'tracking/w_lookup', 15)
        self.register_config_handler(self.w_anki_word, 'tracking/w_anki_word', 70)
        self.register_config_handler(self.w_anki_ctx, 'tracking/w_anki_ctx', 30)
        self.register_config_handler(self.w_anki_word_y, 'tracking/w_anki_word_y', 40)
        self.register_config_handler(self.w_anki_ctx_y, 'tracking/w_anki_ctx_y', 20)
        self.register_config_handler(self.known_data_lifetime, 'tracking/known_data_lifetime', 1800)

        self.register_config_handler(self.theme, 'theme', 'auto' if platform.system() !=
                                     "Linux" else 'system')  # default to native on Linux

        
        # Using the previous qdarktheme.setup_theme function would result in having
        # the default accent color when changing theme. Instead, using the setupTheme
        # function does not change the current accent color.
        self.theme.currentTextChanged.connect(self.setupTheme)
        self.anki_query_mature.editingFinished.connect(self.getMatchedCards)
        self.anki_query_young.editingFinished.connect(self.getMatchedCards)
        self.preview_young_button.clicked.connect(self.previewYoung)
        self.preview_mature_button.clicked.connect(self.previewMature)
        self.open_fieldmatcher.clicked.connect(self.openFieldMatcher)
        

    def setAvailable(self):
        #self.api_host.setEnabled(self.api_enabled.isChecked())
        #self.api_port.setEnabled(self.api_enabled.isChecked())
        self.reader_host.setEnabled(self.reader_enabled.isChecked())
        self.reader_port.setEnabled(self.reader_enabled.isChecked())

    def openFieldMatcher(self):
        fieldmatcher = FieldMatcher(self)
        fieldmatcher.exec()

    def toggle_anki_settings(self, value: bool):
        self.anki_api.setEnabled(value)
        self.tags.setEnabled(value)
        self.note_type.setEnabled(value)
        self.deck_name.setEnabled(value)
        self.sentence_field.setEnabled(value)
        self.word_field.setEnabled(value)
        self.frequency_field.setEnabled(value)
        self.definition1_field.setEnabled(value)
        self.definition2_field.setEnabled(value)
        self.pronunciation_field.setEnabled(value)
        self.image_field.setEnabled(value)
        self.anki_query_mature.setEnabled(value)
        self.anki_query_young.setEnabled(value)
        self.preview_mature_button.setEnabled(value)
        self.preview_young_button.setEnabled(value)
        self.open_fieldmatcher.setEnabled(value)

    def setupTheme(self) -> None:
        theme = self.theme.currentText()  # auto, dark, light, system
        if theme == "system":
            return
        accent_color = self.accent_color.text()
        if accent_color == "default":  # default is not a color
            qdarktheme.setup_theme(
                theme=theme
            )
        else:
            qdarktheme.setup_theme(
                theme=theme,
                custom_colors={"primary": accent_color},
            )

    def previewMature(self):
        try:
            _ = getVersion(api := settings.value('anki_api', 'http://127.0.0.1:8765'))
            guiBrowse(api, self.anki_query_mature.text())
        except Exception as e:
            logger.warning(repr(e))

    def previewYoung(self):
        try:
            _ = getVersion(api := settings.value('anki_api', 'http://127.0.0.1:8765'))
            guiBrowse(api, self.anki_query_young.text())
        except Exception as e:
            logger.warning(repr(e))

    def loadDecks(self):
        self.status("Loading decks")
        api = self.anki_api.text()
        decks = getDeckList(api)
        self.deck_name.blockSignals(True)
        self.deck_name.clear()
        self.deck_name.addItems(decks)
        self.deck_name.setCurrentText(settings.value("deck_name"))
        self.deck_name.blockSignals(False)

        note_types = getNoteTypes(api)
        self.note_type.blockSignals(True)
        self.note_type.clear()
        self.note_type.addItems(note_types)
        self.note_type.setCurrentText(settings.value("note_type"))
        self.note_type.blockSignals(False)

    def loadFields(self):
        self.status("Loading fields")
        api = self.anki_api.text()

        current_type = self.note_type.currentText()
        if current_type == "":
            return

        fields = getFields(api, current_type)
        # Temporary store fields
        sent = self.sentence_field.currentText()
        word = self.word_field.currentText()
        freq_stars = self.frequency_field.currentText()
        def1 = self.definition1_field.currentText()
        def2 = self.definition2_field.currentText()
        pron = self.pronunciation_field.currentText()
        img = self.image_field.currentText()

        # Block signals temporarily to avoid warning dialogs
        self.sentence_field.blockSignals(True)
        self.word_field.blockSignals(True)
        self.frequency_field.blockSignals(True)
        self.definition1_field.blockSignals(True)
        self.definition2_field.blockSignals(True)
        self.pronunciation_field.blockSignals(True)
        self.image_field.blockSignals(True)

        self.sentence_field.clear()
        self.sentence_field.addItems(fields)

        self.word_field.clear()
        self.word_field.addItems(fields)

        self.frequency_field.clear()
        self.frequency_field.addItem("<disabled>")
        self.frequency_field.addItems(fields)

        self.definition1_field.clear()
        self.definition1_field.addItems(fields)

        self.definition2_field.clear()
        self.definition2_field.addItem("<disabled>")
        self.definition2_field.addItems(fields)

        self.pronunciation_field.clear()
        self.pronunciation_field.addItem("<disabled>")
        self.pronunciation_field.addItems(fields)

        self.image_field.clear()
        self.image_field.addItem("<disabled>")
        self.image_field.addItems(fields)

        self.sentence_field.setCurrentText(settings.value("sentence_field"))
        self.word_field.setCurrentText(settings.value("word_field"))
        self.frequency_field.setCurrentText(settings.value("frequency_field"))
        self.definition1_field.setCurrentText(settings.value("definition1_field"))
        self.definition2_field.setCurrentText(settings.value("definition2_field"))
        self.pronunciation_field.setCurrentText(settings.value("pronunciation_field"))
        self.image_field.setCurrentText(settings.value("image_field"))

        if self.sentence_field.findText(sent) != -1:
            self.sentence_field.setCurrentText(sent)
        if self.word_field.findText(word) != -1:
            self.word_field.setCurrentText(word)
        if self.frequency_field.findText(freq_stars) != -1:
            self.frequency_field.setCurrentText(freq_stars)
        if self.definition1_field.findText(def1) != -1:
            self.definition1_field.setCurrentText(def1)
        if self.definition2_field.findText(def2) != -1:
            self.definition2_field.setCurrentText(def2)
        if self.pronunciation_field.findText(pron) != -1:
            self.pronunciation_field.setCurrentText(pron)
        if self.image_field.findText(img) != -1:
            self.image_field.setCurrentText(img)

        self.sentence_field.blockSignals(False)
        self.word_field.blockSignals(False)
        self.frequency_field.blockSignals(False)
        self.definition1_field.blockSignals(False)
        self.definition2_field.blockSignals(False)
        self.pronunciation_field.blockSignals(False)
        self.image_field.blockSignals(False)
        self.status("Done")

    def errorNoConnection(self, error):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Error")
        msg.setInformativeText(
            str(error) + "\nAnkiConnect must be running to set Anki-related options."
            "\nIf you have AnkiConnect set up at a different endpoint, set that now "
            "and reopen the config tool.")
        msg.exec()

    @pyqtSlot(bool)
    def changeMainLayout(self, checked: bool):
        if checked:
            # This means user has changed from one source to two source mode,
            # need to redraw main window
            if settings.value("orientation", "Vertical") == "Vertical":
                self.parent._layout.removeWidget(self.parent.definition)
                self.parent._layout.addWidget(
                    self.parent.definition, 6, 0, 2, 3)
                self.parent._layout.addWidget(
                    self.parent.definition2, 8, 0, 2, 3)
                self.parent.definition2.setVisible(True)
        else:
            self.parent._layout.removeWidget(self.parent.definition)
            self.parent._layout.removeWidget(self.parent.definition2)
            self.parent.definition2.setVisible(False)
            self.parent._layout.addWidget(self.parent.definition, 6, 0, 4, 3)

    def status(self, msg):
        self.status_bar.showMessage(self.parent.time() + " " + msg, 4000)

    def register_config_handler(self, *args, **kwargs): # pylint: disable=unused-argument
        logger.error("register_config_handler is being called!")
