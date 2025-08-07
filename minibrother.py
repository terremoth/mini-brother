''' Mini Brother is a JavaScript Intolerant Browser by Terremoth '''
import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QTabWidget, QLabel, 
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineScript, QWebEngineSettings, QWebEngineProfile, QWebEnginePage
from PyQt5.QtCore import QUrl, pyqtSlot
from PyQt5.QtGui import QFont
from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo
import requests
from bs4 import BeautifulSoup

HISTORY_FILE = "history.txt"
FONT_DEFAULT_SIZE = 11
DEFAULT_PAGE = "https://www.google.com"
BLOCKED_EXTENSIONS = [
    '.js', '.mjs', '.cjs', '.jsx', '.tsx',
    '.json','.wasm','.map','.worker.js','.prod','.nexus',
    '.sw.js','.manifest', '.jsonp', '.swf'
]


class BrowserTab(QWidget):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        font = QFont()
        font.setPointSize(FONT_DEFAULT_SIZE)
        
        class PageWithCreateWindow(QWebEnginePage):
            def createWindow(inner_self, _type):
                browser = self.window()
                if hasattr(browser, 'add_new_tab'):
                    new_tab = browser.add_new_tab("about:blank")
                    return new_tab.webview.page()
                return super(PageWithCreateWindow, inner_self).createWindow(_type)
            
            
            def javaScriptAlert(inner_self, url, msg):
                print(f"JavaScript alert blocked from {url}: {msg}")
                return True
            
            def javaScriptConfirm(inner_self, url, msg):
                print(f"JavaScript confirm blocked from {url}: {msg}")
                return False
            
            def javaScriptPrompt(inner_self, url, msg, defaultValue):
                print(f"JavaScript prompt blocked from {url}: {msg}")
                return (False, "")
            
            def javaScriptConsoleMessage(inner_self, level, message, lineNumber, sourceID):
                #print(f"JS console: {message}")
                pass
        
        self.webview = QWebEngineView()
        
        settings = self.webview.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, False)
        settings.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, False)
        settings.setAttribute(QWebEngineSettings.JavascriptCanAccessClipboard, False)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, False)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, False)
        settings.setAttribute(QWebEngineSettings.XSSAuditingEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, False)
        settings.setAttribute(QWebEngineSettings.WebGLEnabled, False)
        settings.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, False)
        settings.setAttribute(QWebEngineSettings.AutoLoadImages, True)  # Manter imagens
        settings.setAttribute(QWebEngineSettings.DnsPrefetchEnabled, False)
        settings.setAttribute(QWebEngineSettings.HyperlinkAuditingEnabled, False)
        settings.setAttribute(QWebEngineSettings.JavascriptCanPaste, False)
        
        try:
            settings.setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, True)
            settings.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, False)
            settings.setAttribute(QWebEngineSettings.AllowGeolocationOnInsecureOrigins, False)
        except AttributeError:
            pass
        
        self.webview.setPage(PageWithCreateWindow(profile, self.webview))

        # History buttons
        self.back_btn = QPushButton("<")
        self.forward_btn = QPushButton(">")

        self.back_btn.clicked.connect(self.webview.back)
        self.forward_btn.clicked.connect(self.webview.forward)

        # Address bar
        self.address_bar = QLineEdit()
        self.address_bar.returnPressed.connect(self.load_url)

        # Go button
        self.go_button = QPushButton("Go!")
        self.go_button.clicked.connect(self.load_url)

        # Layout top bar
        top_bar = QHBoxLayout()
        top_bar.addWidget(self.back_btn)
        top_bar.addWidget(self.forward_btn)
        top_bar.addWidget(self.address_bar)
        top_bar.addWidget(self.go_button)

        # Main layout
        layout = QVBoxLayout()
        layout.addLayout(top_bar)
        layout.addWidget(self.webview)
        
        self.back_btn.setFont(font)
        self.forward_btn.setFont(font)
        self.address_bar.setFont(font)
        self.go_button.setFont(font)

        self.setLayout(layout)

        # Connect signals to update address bar and buttons
        self.webview.urlChanged.connect(self.update_url)
        self.webview.loadFinished.connect(self.update_buttons)
        self.webview.titleChanged.connect(self.update_tab_title)

        # Load default page
        self.navigate_to(DEFAULT_PAGE)

    def load_url(self):
        url = self.address_bar.text().strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        self.navigate_to(url)

    def navigate_to(self, url):
        if not isinstance(url, str):
            url = DEFAULT_PAGE
            
        self.address_bar.setText(url)
        
        cleaned_html = self.get_and_clean_html(url)
        print("Got cleaned html!")
        
        self.webview.setHtml(cleaned_html, baseUrl=QUrl(url))
        

    @pyqtSlot(QUrl)
    def update_url(self, qurl):
        self.address_bar.setText(qurl.toString())
        self.save_history(qurl)

    @pyqtSlot(bool)
    def update_buttons(self, ok):
        self.back_btn.setEnabled(self.webview.history().canGoBack())
        self.forward_btn.setEnabled(self.webview.history().canGoForward())

    @pyqtSlot(str)
    def update_tab_title(self, title):
        parent = self.parent()
        if parent is not None:
            if not hasattr(parent, "setTabText"):
                parent = parent.parent()

        if parent:
            index = parent.indexOf(self)
            if index != -1:
                max_len = 32
                display_title = title if title else "New Tab"
                if len(display_title) > max_len:
                    display_title = display_title[:max_len - 3] + "..."

                parent.setTabText(index, display_title)
                parent.setTabToolTip(index, title)

    def save_history(self, qurl):
        url = qurl.toString()
        try:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(url + "\n")
        except Exception as e:
            print("Failed to save history:", e)
            
            
    def get_and_clean_html(self, url):
        try:
            headers = {'User-Agent': 'MinimalBrowser/1.0'}
            response = requests.get(url, headers=headers, timeout=10) 
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            for script_tag in soup.find_all('script'):
                script_tag.decompose() # .decompose() remove tags 
            
            for link_tag in soup.find_all('link'):
                rel = link_tag.get('rel')
                as_attr = link_tag.get('as')
                href = link_tag.get('href')
                
                if as_attr == 'script':
                    link_tag.decompose()
                elif href and href.endswith('.js'):
                    link_tag.decompose()
                elif rel == 'stylesheet' and href and any(ext in href.lower() for ext in BLOCKED_EXTENSIONS):
                    link_tag.decompose()
                    
            return str(soup)

        except requests.exceptions.RequestException as e:
            print(f"Error downloading URL: {url}: {e}")
            return f"<html><body><h1>Error on loading pages</h1><p>{e}</p></body></html>"
            

class Browser(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.profile = QWebEngineProfile("NoJSProfile", self)
        
        interceptor = ResourceBlocker(self)
        self.profile.setUrlRequestInterceptor(interceptor)
        
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)
        self.profile.setCachePath("") 
        self.profile.setPersistentStoragePath("") 
        self.profile.setHttpUserAgent("MinimalBrowser/1.0")
        self.profile.setHttpCacheType(QWebEngineProfile.NoCache)
        
        try:
            self.profile.setSpellCheckEnabled(False)
        except AttributeError:
            pass

        font = QFont()
        font.setPointSize(FONT_DEFAULT_SIZE)
        
        self.setWindowTitle("Mini Brother - A JavaScript intolerant browser")
        self.setGeometry(100, 100, 900, 700)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        self.tabs.setFont(font)

        self.setCentralWidget(self.tabs)

        self.new_tab_btn = QPushButton("+")
        self.new_tab_btn.setFixedWidth(30)
        self.new_tab_btn.clicked.connect(self.add_new_tab)
        self.new_tab_btn.setFont(font)

        self.tabs.setCornerWidget(self.new_tab_btn)

        self.add_new_tab()

    def add_new_tab(self, url=DEFAULT_PAGE):
        new_tab = BrowserTab(self.profile, self.tabs)
        self.tabs.addTab(new_tab, "New Tab")
        self.tabs.setCurrentWidget(new_tab)
        new_tab.navigate_to(url)
        return new_tab

    def close_tab(self, index):
        widget = self.tabs.widget(index)
        if widget:
            self.tabs.removeTab(index)
            widget.deleteLater()

        if self.tabs.count() == 0:
            self.close()

    def on_tab_changed(self, index):
        current_tab = self.tabs.widget(index)
        if current_tab:
            title = current_tab.webview.title()
            self.setWindowTitle(f"Mini Brother - A JavaScript intolerant browser")


class ResourceBlocker(QWebEngineUrlRequestInterceptor):
    def interceptRequest(self, info):
        url = info.requestUrl().toString().lower()
        resource_type = info.resourceType()
        
        blocked_types = [
            QWebEngineUrlRequestInfo.ResourceTypeXhr,           
            QWebEngineUrlRequestInfo.ResourceTypeScript,        
            QWebEngineUrlRequestInfo.ResourceTypeSubResource,        
            QWebEngineUrlRequestInfo.ResourceTypeWorker,       
            QWebEngineUrlRequestInfo.ResourceTypeSharedWorker,       
            QWebEngineUrlRequestInfo.ResourceTypeServiceWorker,        
            QWebEngineUrlRequestInfo.ResourceTypeCspReport,        
            QWebEngineUrlRequestInfo.ResourceTypePluginResource,        
            QWebEngineUrlRequestInfo.ResourceTypeNavigationPreloadMainFrame,    
            QWebEngineUrlRequestInfo.ResourceTypeNavigationPreloadSubFrame,       
            QWebEngineUrlRequestInfo.ResourceTypeUnknown,      
            QWebEngineUrlRequestInfo.ResourceTypePing,  
        ]

        if resource_type in blocked_types:
            #print(f"Resource type blocked: {resource_type} - {url}")
            info.block(True)
            return

        
        blocked_patterns = [
           
        ]
        
        if any(url.endswith(ext) for ext in BLOCKED_EXTENSIONS):
            #print(f"Extension blocked: {url}")
            info.block(True)
            return
        
        if any(pattern in url for pattern in blocked_patterns):
            #print(f"Pattern blocked: {url}")
            info.block(True)
            return
        
        js_params = ['callback=', 'jsonp=', '_callback=', 'cb=']
        if any(param in url for param in js_params):
            #print(f"JS parameter blocked: {url}")
            info.block(True)
            return
        
        #print(f"Resource allowed: {resource_type} - for:", url)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    browser = Browser()
    browser.show()
    sys.exit(app.exec_())
