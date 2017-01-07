# Keypirinha | A semantic launcher for Windows | http://keypirinha.com

import keypirinha as kp
import keypirinha_util as kpu
import keypirinha_net as kpn
import keypirinha_api
import os
import datetime
import urllib
import urllib.request
import json

class Bookmark():
    def __init__(self, tags, label, url):
        self.tags = tags
        self.label = label.strip() if isinstance(label, str) else ""
        self.url = url.strip() if isinstance(url, str) else ""

        self.scheme = None
        self.empty_label = False
        self.is_auth = False
        self.pretty_url = self.url

        try:
            parsed = urllib.parse.urlparse(self.url)

            self.scheme = parsed.scheme

            if parsed.username or parsed.password:
                self.is_auth = True

            self.pretty_url = parsed.hostname + parsed.path
        except Exception:
            pass

        if not self.label:
            self.empty_label = True
            self.label = self.pretty_url

class Pinboard(kp.Plugin):
    """Launch Pinboard bookmarks."""

    # Constants
    CONFIG_SECTION_MAIN = "main"
    DEFAULT_ITEM_LABEL = "Pinboard"
    DEFAULT_ITEM_DESC = "Search and open bookmarks from pinboard.in"
    DEFAULT_ITEM_LABEL_FORMAT = "Pinboard: {label} ({tags})"
    DEFAULT_ALWAYS_SUGGEST = False
    DEFAULT_KEEP_EMPTY_NAMES = True
    DEFAULT_KEEP_AUTH_URL = True
    DEFAULT_FORCE_NEW_WINDOW = None
    DEFAULT_FORCE_PRIVATE_MODE = None
    DEFAULT_BOOKMARK_REFRESH = 14400
    DEFAULT_BOOKMARK_FILE = None
    DEFAULT_TOREAD_TAG = "#toread"
    DEFAULT_API_TOKEN = None
    DEFAULT_API_BASE = "https://api.pinboard.in/v1/posts/all"
    DEFAULT_API_FORMAT = "json"
    DEFAULT_API_FILE = "pinboard.json"
    KEYWORD = "Pinboard"
        
    # Variables
    item_label = DEFAULT_ITEM_LABEL
    item_label_format = DEFAULT_ITEM_LABEL_FORMAT
    always_suggest = DEFAULT_ALWAYS_SUGGEST
    keep_empty_names = DEFAULT_KEEP_EMPTY_NAMES
    keep_auth_url = DEFAULT_KEEP_AUTH_URL
    force_new_window = DEFAULT_FORCE_NEW_WINDOW
    force_private_mode = DEFAULT_FORCE_PRIVATE_MODE
    bookmark_refresh = DEFAULT_BOOKMARK_REFRESH
    bookmark_file = DEFAULT_BOOKMARK_FILE
    api_token = DEFAULT_API_TOKEN
    api_base = DEFAULT_API_BASE
    api_format = DEFAULT_API_FORMAT
    api_file = DEFAULT_API_FILE
    
    def __init__(self):
        super().__init__()
        #self._debug = True
        self.dbg("CONSTRUCTOR")

    def on_start(self):
        self.dbg("On Start")

        self._read_config()

    def on_catalog(self):
        self.dbg("On Catalog")
        
        self.set_catalog([self._create_keyword_item(label=self.item_label + "...",short_desc=self.DEFAULT_ITEM_DESC)])
        self._download_bookmarks()
        
        if self.always_suggest:
            catalog = []
            bookmarks = self._list_bookmarks()
            if not bookmarks == None and not len(bookmarks) == 0:
                for b in bookmarks:
                    if not b.label or not b.url:
                        continue
                    if b.empty_label and not self.keep_empty_names:
                        continue
                    if b.is_auth and not self.keep_auth_url:
                        continue
                    if "script" in b.scheme.lower(): # javascript, vbscript, ...
                        continue
                    catalog.append(self._create_url_item(b.label, b.tags, "", b.url)) 

            self.set_catalog(catalog)
            self.info("Referenced {} bookmark{}".format(len(catalog), "s"[len(catalog)==1:]))

    def on_suggest(self, user_input, items_chain):
        self.dbg('On Suggest "{}" (items_chain[{}])'.format(user_input, len(items_chain)))
        
        if not self.always_suggest:
            if not items_chain and (not self.always_suggest or len(user_input) == 0):
                return

            if items_chain and (
                items_chain[0].category() != kp.ItemCategory.KEYWORD or
                items_chain[0].target() != self.KEYWORD):
                return

            suggestions = []
            bookmarks = self._list_bookmarks()
            if not bookmarks == None and not len(bookmarks) == 0:
                for b in bookmarks:
                    if not b.label or not b.url:
                        continue
                    if b.empty_label and not self.keep_empty_names:
                            continue
                    if b.is_auth and not self.keep_auth_url:
                        continue
                    if "script" in b.scheme.lower(): # javascript, vbscript, ...
                        continue
                    suggestions.append(self._create_url_item(b.label, b.tags, "", b.url)) 
                   
            if len(suggestions) > 0:
                self.set_suggestions(suggestions, kp.Match.DEFAULT, kp.Sort.NONE)

    def on_execute(self, item, action):
        self.dbg("On execute (item {} : action {})".format(item, action))
        
        if action:
            kpu.execute_default_action(self, item, action)
        else:
            kpu.web_browser_command(
                private_mode=self.force_private_mode,
                new_window=self.force_new_window,
                url=item.target(),
                execute=True)

    def on_events(self, flags):
        self.dbg("On events (flags {:#x})".format(flags))
        
        if flags & kp.Events.PACKCONFIG:
            self._read_config()

    def _read_config(self):
        self.dbg("Read Config")
        
        settings = self.load_settings()
        
        self.api_token = settings.get(
            "api_token", 
            self.CONFIG_SECTION_MAIN,
            self.DEFAULT_API_TOKEN)
        
        self.bookmark_refresh = settings.get(
            "bookmark_refresh",
            self.CONFIG_SECTION_MAIN,
            self.DEFAULT_BOOKMARK_REFRESH)
        
        self.item_label = settings.get(
            "item_label", 
            self.CONFIG_SECTION_MAIN,
            self.DEFAULT_ITEM_LABEL)

        self.item_label_format = settings.get(
            "item_label_format", 
            self.CONFIG_SECTION_MAIN,
            self.DEFAULT_ITEM_LABEL_FORMAT)
            
        self.always_suggest = settings.get_bool(
            "always_suggest", 
            self.CONFIG_SECTION_MAIN,
            self.DEFAULT_ALWAYS_SUGGEST)
            
        self.keep_empty_names = settings.get_bool(
            "keep_empty_names", 
            self.CONFIG_SECTION_MAIN,
            self.DEFAULT_KEEP_EMPTY_NAMES)
            
        self.keep_auth_url = settings.get_bool(
            "keep_auth_url", 
            self.CONFIG_SECTION_MAIN,
            self.DEFAULT_KEEP_AUTH_URL)
            
        self.force_new_window = settings.get_bool(
            "force_new_window", 
            self.CONFIG_SECTION_MAIN,
            self.DEFAULT_FORCE_NEW_WINDOW)
            
        self.force_private_mode = settings.get_bool(
            "force_private_mode", 
            self.CONFIG_SECTION_MAIN,
            self.DEFAULT_FORCE_PRIVATE_MODE)
        
    def _create_keyword_item(self, label, short_desc):
        return self.create_item(
            category=kp.ItemCategory.KEYWORD,
            label=label,
            short_desc=short_desc,
            target=self.KEYWORD,
            args_hint=kp.ItemArgsHint.REQUIRED,
            hit_hint=kp.ItemHitHint.NOARGS
        )

    def _create_url_item(self, label, tags, short_desc, target):
        return self.create_item(
            category=kp.ItemCategory.URL,
            label=self.item_label_format.format(label=label, tags=tags),
            short_desc=short_desc,
            target=target,
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.NOARGS
        )
        
    def _download_bookmarks(self):
        self.dbg("Download Bookmarks")
        
        if self.api_token:
            if not len(self.api_token) > 0:
                self.info("API token is not valid.")
        
        self.api_url = self.api_base + "?auth_token=" + self.api_token + "&format=" + self.api_format
        self.bookmark_path = self.get_package_cache_path(create=True)
        
        if os.path.isdir(self.bookmark_path):
            self.bookmark_file = self.bookmark_path + "\\" + self.api_file
            
            if os.path.isfile(self.bookmark_file):
                today = datetime.datetime.today()
                file_modified = datetime.datetime.fromtimestamp(os.path.getmtime(self.bookmark_file))
                delta = today - file_modified

                if delta.seconds > self.bookmark_refresh:
                    self._write_file(self.bookmark_file, self._fetch_bookmarks())
            else:
                self._write_file(self.bookmark_file, self._fetch_bookmarks())
    
    def _fetch_bookmarks(self):
        self.dbg("Fetch Bookmarks")
        
        try:
            opener = kpn.build_urllib_opener()
            response = opener.open(self.api_url)
        except:
            self.info("Pinboard website could not be reached!")
        
        return response.read()
    
    def _write_file(self, file, content):
        self.dbg("Write File")
        
        handle = None
        
        if isinstance(content, str):
            handle = open(file, 'w')
        elif isinstance(content, bytes):
            handle = open(file, 'wb')
        
        handle.write(content)  
        handle.close()
    
    def _list_bookmarks(self):
        self.dbg("List Bookmarks")
        
        if not os.path.isfile(self.bookmark_file):
            self._download_bookmarks()
        
        file_content = open(self.bookmark_file)
        bookmark_data = json.load(file_content)
        
        bookmarks = []
        for bookmark in bookmark_data:
            tags = bookmark['tags']
            toread = None
            
            if bookmark['toread'] == "yes":
                if len(tags) == 0:
                    tags = self.DEFAULT_TOREAD_TAG
                else:
                    tags = self.DEFAULT_TOREAD_TAG + " " + tags

            bookmarks.append(Bookmark(tags, bookmark['description'], bookmark['href']))
            
        return bookmarks