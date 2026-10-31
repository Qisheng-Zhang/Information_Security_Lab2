"""Qt 工作台的视觉系统、矢量图标及页面布局。"""

import re

from PySide6.QtCore import QPointF, QRectF, QSize, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QComboBox, QFrame, QGraphicsDropShadowEffect, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPlainTextEdit, QProgressBar,
    QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QTableWidget,
    QVBoxLayout, QWidget,
)

ACCENT = "#7D6E98"
INK = "#514958"
MUTED = "#9296A4"
FONT = "Microsoft YaHei UI"

from .version import __version__

STYLE = """
QMainWindow, QWidget#Workspace { background:#FAF7F2; }
QWidget { font-family:'Microsoft YaHei UI'; font-size:14px; color:#57515D; }
QLabel { background:transparent; border:none; }
QFrame#Sidebar { background:#FFFCF7; border-right:1px solid #EDE6DE; }
QLabel#Brand { color:#574D60; font-size:18px; font-weight:700; }
QLabel#Tiny { color:#978B9C; font-size:11px; }
QLabel#Section { color:#AB9EAC; font-size:11px; }
QLabel#NavTitle { color:#7F7289; font-size:13px; }
QLabel#NavNote { color:#AEA0B0; font-size:11px; }
QPushButton#NavItem { background:transparent; border:1px solid transparent; border-radius:10px; text-align:left; }
QPushButton#NavItem:hover { background:#F6F0F5; }
QPushButton#NavItem[selected=true] { background:#F0E9F4; border:1px solid #E6DCEC; }
QPushButton#NavItem[selected=true] QLabel#NavTitle { color:#8B739F; font-weight:600; }
QPushButton#NavItem[selected=true] QLabel#NavNote { color:#AD9AB9; }
QFrame#SidebarNote { background:#F6F0F5; border-radius:10px; }
QLabel#Breadcrumb { color:#A597A9; font-size:11px; }
QLabel#PageTitle { color:#514758; font-size:26px; font-weight:700; }
QLabel#Subtitle { color:#998B9F; font-size:13px; }
QLabel#PageIndex { color:#C3B7CA; font-family:'Consolas'; font-size:12px; }
QLabel#Badge { color:#9D8AAC; background:#F5EEF7; border:1px solid #EBE0EF; border-radius:12px; padding:4px 10px; font-size:10px; }
QLabel#Online { color:#A398A6; font-size:10px; }
QFrame#Card { background:#FFFEFB; border:1px solid #EEE7E0; border-radius:16px; }
QFrame#Card[featured=true] { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #F1EAF6,stop:1 #EFF3F7); border:1px solid #E6DEED; }
QLabel#CardTitle { color:#62566D; font-size:15px; font-weight:600; }
QLabel#Eyebrow { color:#BCAFBE; font-size:9px; letter-spacing:1px; }
QLabel#CardNote { color:#9C8FA1; font-size:11px; }
QLabel#FieldLabel { color:#8D7F94; font-size:12px; }
QLineEdit { color:#796984; background:#FDFBF8; border:1px solid #EDE3E7; border-radius:8px; padding:9px 12px; selection-background-color:#EDE0F4; }
QLineEdit:focus { border:1px solid #BCA7CA; background:#FFFEFB; }
QLineEdit[mono=true] { font-family:'Consolas'; font-size:16px; }
QLineEdit[invalid=true] { border:1px solid #C98D94; background:#FFF6F4; }
QComboBox { background:#FDFBF8; border:1px solid #EDE3E7; border-radius:8px; padding:9px 12px; min-height:17px; }
QComboBox:hover { border-color:#D4C0DD; }
QComboBox::drop-down { border:none; width:26px; }
QComboBox::down-arrow { image:none; width:0px; height:0px; border:none; }
QComboBox QAbstractItemView { border:1px solid #E5E5EF; padding:6px; background:white; selection-background-color:#F0E9F4; outline:0; }
QPushButton { background:white; color:#93809F; border:1px solid #E8DDEA; border-radius:8px; padding:9px 14px; font-size:12px; }
QPushButton:hover { border-color:#CCB6D7; color:#8F719E; background:#FBF6FD; }
QPushButton:pressed { background:#F1E7F5; }
QPushButton:focus { border:1px solid #B8A0C9; }
QPushButton[primary=true] { background:#7D6E98; border:1px solid #7D6E98; color:white; font-weight:600; }
QPushButton[primary=true]:hover { background:#8D7CA9; border-color:#8D7CA9; }
QPushButton[primary=true]:pressed { background:#6D5E89; }
QPushButton:disabled { color:#C6BACD; background:#F7F2F8; border-color:#EEE5F0; }
QPushButton[ghost=true] { border:none; background:transparent; padding:6px 8px; color:#AB98B5; }
QPushButton[ghost=true]:hover { background:#F6EFF9; color:#7D6E98; }
QPushButton[onResult=true] { background:#EAE2F0; border:1px solid #DDCFE6; color:#9680A5; }
QPushButton[onResult=true]:hover { background:#E3D7ED; border-color:#CBB6DB; }
QLabel#Output { color:#786789; font-family:'Consolas'; font-size:51px; font-weight:600; letter-spacing:4px; }
QLabel#OutputMeta { color:#A392B0; font-size:11px; }
QLabel#Binary { color:#A8ACC7; font-family:'Consolas'; font-size:14px; letter-spacing:1px; }
QLabel#ResultTag { color:#789469; background:#E8F0E1; border:1px solid #D9E4CF; border-radius:10px; padding:3px 9px; font-size:10px; }
QLabel#ResultTag[dirty=true] { color:#B08B59; background:#F6EDDF; border-color:#E9D7B8; }
QLabel#KeyChip { color:#A38DB1; background:#F6EFFA; border:1px solid #EBDEF3; border-radius:6px; padding:5px 10px; font-family:'Consolas'; font-size:11px; }
QLabel#KeyChip[tone="1"] { color:#849BB2; background:#F0F5FA; border-color:#DCE6EE; }
QLabel#KeyChip[tone="2"] { color:#90A17F; background:#F2F6EB; border-color:#E1E9D6; }
QLabel#BitGroup { color:#9A85AB; background:#FDF9FF; border:1px solid #E8DCF0; border-radius:7px; padding:7px 10px; font-family:'Consolas'; font-size:14px; }
QPushButton[filter=true] { background:transparent; border:1px solid transparent; border-radius:7px; padding:6px 10px; color:#AD9AB8; font-size:11px; }
QPushButton[filter=true]:checked { background:#F0E7F7; border:1px solid #E3D3ED; color:#977BA8; }
QLabel#StepValue { color:#9E83B0; font-family:'Consolas'; font-size:18px; }
QLabel#Summary { color:#7F9870; background:#F0F5E9; border:1px solid #E2EBD6; border-radius:8px; padding:12px; font-family:'Consolas'; font-size:13px; }
QPlainTextEdit { background:#FDFBF8; border:1px solid #EEE5E8; border-radius:9px; padding:11px; color:#8A7C93; font-family:'Consolas'; font-size:13px; selection-background-color:#EBDCF3; }
QPlainTextEdit:focus { border:1px solid #BCA7CA; background:#FFFEFB; }
QPlainTextEdit[code=true] { color:#A28BAB; background:#FCF9FB; }
QPlainTextEdit[readonly=true] { background:#FFFCF7; color:#85728D; }
QTableWidget { background:#FFFEFB; border:none; gridline-color:#F4EDF5; selection-background-color:#F5ECF9; selection-color:#9479A6; outline:0; font-size:12px; }
QTableWidget::item { padding:0px 9px; border:none; }
QHeaderView::section { background:#FFFCF7; border:none; border-bottom:1px solid #F3EDF5; padding:9px; color:#AD99B6; font-size:11px; font-weight:400; }
QScrollBar:vertical { width:6px; background:transparent; margin:4px 0; }
QScrollBar::handle:vertical { background:#E7D9ED; border-radius:3px; min-height:24px; }
QScrollBar::handle:vertical:hover { background:#D3BDD9; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:none; }
QScrollBar:horizontal { height:6px; background:transparent; }
QScrollBar::handle:horizontal { background:#E7D9ED; border-radius:3px; min-width:24px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width:0; }
QProgressBar { border:none; background:#F4EBF8; border-radius:3px; max-height:6px; min-height:6px; }
QProgressBar::chunk { background:#C0ACD0; border-radius:3px; }
QLabel#Status { color:#AF9CB7; font-size:11px; }
QLabel#Status[error=true] { color:#C78990; }
QLabel#Preview { color:#AF927B; background:#FCF3E8; border:1px solid #F0E1CE; border-radius:9px; padding:13px; font-family:'Consolas'; font-size:12px; }
QToolTip { background:#8C799C; color:white; border:none; padding:7px; }
"""


def icon(name, color="#B19DBC", size=20):
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 24, size / 24)
    painter.setPen(QPen(QColor(color), 1.65, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    def line(x1,y1,x2,y2): painter.drawLine(QPointF(x1,y1),QPointF(x2,y2))
    if name in ("lock", "unlock"):
        painter.drawRoundedRect(QRectF(5,10,14,11),2,2)
        path=QPainterPath(QPointF(8,10)); path.lineTo(8,7); path.cubicTo(8,1,16,1,16,7)
        if name=="lock": path.lineTo(16,10)
        painter.drawPath(path); line(12,14,12,17)
    elif name=="grid":
        for x,y in ((4,4),(14,4),(4,14),(14,14)): painter.drawRoundedRect(QRectF(x,y,6,6),1.5,1.5)
    elif name=="link":
        painter.save()
        painter.translate(12,12)
        painter.rotate(-45)
        painter.drawRoundedRect(QRectF(-9,-3,11,6),3,3)
        painter.drawRoundedRect(QRectF(-2,-3,11,6),3,3)
        painter.restore()
    elif name=="text":
        line(4,5,20,5); line(12,5,12,20); line(8,20,16,20); line(4,5,4,8); line(20,5,20,8)
    elif name=="layers":
        painter.drawPolygon([QPointF(3,8),QPointF(12,3),QPointF(21,8),QPointF(12,13)])
        for y in (13,18): line(3,y,12,y+5); line(12,y+5,21,y)
    elif name=="chain":
        for x in (2,16): painter.drawRoundedRect(QRectF(x,8,6,8),1.5,1.5)
        line(8,12,16,12); line(12,9,16,12); line(12,15,16,12)
    elif name=="shuffle":
        for a,b,c,d in ((3,6,7,6),(7,6,17,18),(3,18,7,18),(7,18,17,6),(17,6,21,6),(17,18,21,18),(18,3,21,6),(21,6,18,9),(18,15,21,18),(21,18,18,21)): line(a,b,c,d)
    elif name in ("arrow","back","import","export"):
        if name=="back": painter.translate(24,24); painter.rotate(180)
        if name in ("import","export"):
            painter.drawRoundedRect(QRectF(3,13,18,8),2,2)
            if name=="export": painter.translate(24,15); painter.rotate(180)
            line(12,2,12,14); line(8,10,12,14); line(16,10,12,14)
        else: line(4,12,20,12); line(15,7,20,12); line(15,17,20,12)
    elif name=="copy":
        painter.drawRoundedRect(QRectF(8,8,12,13),2,2); line(5,16,3,16); line(3,16,3,3); line(3,3,15,3); line(15,3,15,5)
    elif name=="check":
        painter.drawEllipse(QRectF(3,3,18,18)); line(7,12,10,15); line(10,15,17,8)
    elif name=="play": painter.drawPolygon([QPointF(8,5),QPointF(19,12),QPointF(8,19)])
    elif name=="stop": painter.drawRoundedRect(QRectF(6,6,12,12),2,2)
    elif name=="key":
        painter.drawEllipse(QRectF(3,3,9,9)); line(10,11,21,21); line(17,17,20,14); line(14,14,17,11)
    elif name=="info":
        painter.drawEllipse(QRectF(3,3,18,18)); line(12,11,12,17); painter.drawPoint(QPointF(12,7))
    else: painter.drawRoundedRect(QRectF(4,4,16,16),4,4)
    painter.end()
    return QIcon(pixmap)


def label(text="", name="", wrap=False):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def row(*widgets, spacing=10):
    layout = QHBoxLayout()
    layout.setContentsMargins(0,0,0,0)
    layout.setSpacing(spacing)
    for widget in widgets:
        if isinstance(widget,int): layout.addStretch(widget)
        elif isinstance(widget,QWidget): layout.addWidget(widget)
        else: layout.addLayout(widget)
    return layout


def button(text, callback, glyph=None, primary=False, ghost=False, on_result=False):
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.setProperty("primary",primary)
    widget.setProperty("ghost",ghost)
    widget.setProperty("onResult",on_result)
    widget.setMinimumHeight(35 if ghost else 38)
    if glyph: widget.setIcon(icon(glyph,"#FFFDFB" if primary else "#A38CB3" if on_result else "#B39DBF",16))
    widget.setIconSize(QSize(16,16))
    widget.clicked.connect(lambda _checked=False: callback())
    return widget


class Card(QFrame):
    def __init__(self,title="",subtitle="",featured=False):
        super().__init__()
        self.setObjectName("Card")
        self.setProperty("featured",featured)
        self.body=QVBoxLayout(self)
        self.body.setContentsMargins(22,20,22,20)
        self.body.setSpacing(15)
        if title:
            headings=QVBoxLayout(); headings.setSpacing(3)
            headings.addWidget(label(title,"CardTitle"))
            if subtitle: headings.addWidget(label(subtitle,"CardNote"))
            self.body.addLayout(headings)
        shadow=QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20); shadow.setOffset(0,4); shadow.setColor(QColor(31,37,76,9))
        self.setGraphicsEffect(shadow)


class ResultCard(Card):
    """结果区域的位图纹理直接来自当前 16 bit 结果。"""

    def __init__(self):
        super().__init__(featured=True)
        self.value = 0

    def set_value(self, value):
        self.value = value
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), 16, 16)
        painter.setClipPath(clip)
        origin_x = self.width() - 95
        for index in range(16):
            active = bool(self.value & (1 << (15 - index)))
            painter.setPen(QPen(QColor(164, 142, 185, 45), 1))
            painter.setBrush(QColor(162, 143, 188, 55 if active else 8))
            painter.drawRoundedRect(
                QRectF(origin_x + index % 4 * 16, 52 + index // 4 * 16, 10, 10),
                2.5, 2.5,
            )


class NavButton(QPushButton):
    def __init__(self,title,note,glyph,index,callback):
        super().__init__()
        self.setObjectName("NavItem"); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(66); self.glyph=glyph
        layout=QHBoxLayout(self); layout.setContentsMargins(13,9,10,9); layout.setSpacing(12)
        self.symbol=QLabel(); self.symbol.setFixedSize(21,21); layout.addWidget(self.symbol)
        words=QVBoxLayout(); words.setSpacing(4)
        words.addWidget(label(title,"NavTitle")); words.addWidget(label(note,"NavNote"))
        layout.addLayout(words,1); layout.addWidget(label(f"0{index+1}","Tiny"))
        for child in self.findChildren(QWidget): child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.clicked.connect(lambda:callback(index)); self.set_selected(False)

    def set_selected(self,selected):
        self.setProperty("selected",selected)
        self.symbol.setPixmap(icon(self.glyph,ACCENT if selected else "#B4A0BE",20).pixmap(20,20))
        self.style().unpolish(self); self.style().polish(self)
        for child in self.findChildren(QLabel): child.style().unpolish(child); child.style().polish(child)


class StateMatrix(QWidget):
    def __init__(self):
        super().__init__()
        self.value = 0
        self.previous = None
        self.changed_cells = ()
        self.hovered_cell = None
        self.setFixedSize(144,144)
        self.setMouseTracking(True)

    def set_value(self, value, previous=None):
        self.value = value
        self.previous = previous
        shifts = (12, 4, 8, 0)
        self.changed_cells = tuple(
            index for index, shift in enumerate(shifts)
            if previous is not None and ((value ^ previous) >> shift) & 15
        )
        self.update()

    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        values=(self.value>>12,(self.value>>4)&15,(self.value>>8)&15,self.value&15)
        for index,value in enumerate(values):
            x=(index%2)*74; y=(index//2)*74
            changed = index in self.changed_cells
            pastel_fills = ("#EEE5F5", "#E7EFF5", "#E8F0E1", "#F6EADF")
            pastel_edges = ("#DFD1EA", "#D3E0EA", "#D7E2CC", "#ECD9C6")
            pastel_inks = ("#8F76A0", "#7191AB", "#81996C", "#AC8D70")
            painter.setPen(QPen(QColor(pastel_edges[index] if changed else "#EEE5EC"), 1))
            if index == self.hovered_cell:
                painter.setPen(QPen(QColor("#B29FC1"), 1.4))
            painter.setBrush(QColor(pastel_fills[index] if changed else "#FDF9FA"))
            painter.drawRoundedRect(QRectF(x+1,y+1,67,67),11,11)
            painter.setPen(QColor("#839576" if changed else "#BBAFC2"))
            coordinate_font = QFont("Consolas"); coordinate_font.setPixelSize(9)
            painter.setFont(coordinate_font)
            painter.drawText(QRectF(x+8,y+5,50,16),f"s{index//2}{index%2}")
            painter.setPen(QColor(pastel_inks[index] if changed else "#AD9AB9"))
            painter.setFont(QFont("Consolas",20))
            painter.drawText(QRectF(x,y+13,69,50),Qt.AlignmentFlag.AlignCenter,f"{value:X}")

    def mouseMoveEvent(self, event):
        column = min(1, int(event.position().x()) // 74)
        row_index = min(1, int(event.position().y()) // 74)
        self.hovered_cell = row_index * 2 + column
        shift = (12, 4, 8, 0)[self.hovered_cell]
        value = (self.value >> shift) & 15
        self.setToolTip(f"s{row_index}{column}   HEX {value:X}   BINARY {value:04b}")
        self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.hovered_cell = None
        self.update()
        super().leaveEvent(event)


class BinaryStrip(QWidget):
    """把 16 bit 结果分成四组，保持与半字节状态的对应关系。"""

    def __init__(self):
        super().__init__()
        self._text = ""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.groups = []
        for _ in range(4):
            group = label("0000", "BitGroup")
            group.setMinimumWidth(51)
            group.setAlignment(Qt.AlignmentFlag.AlignCenter)
            group.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.groups.append(group)
            layout.addWidget(group)
        layout.addStretch()
        self.setText("0000 0111 0011 1000")

    def setText(self, text):
        self._text = text
        for group, value in zip(self.groups, text.split()):
            group.setText(value)

    def text(self):
        return self._text


class JsonHighlighter(QSyntaxHighlighter):
    """对交换数据着色，不修改编辑器中的原始 JSON 文本。"""

    def highlightBlock(self, text):
        number = QTextCharFormat()
        number.setForeground(QColor("#B39877"))
        for match in re.finditer(r"\b\d+\b", text):
            self.setFormat(match.start(), len(match.group()), number)
        for match in re.finditer(r'"(?:\\.|[^"\\])*"', text):
            token = QTextCharFormat()
            token.setForeground(QColor("#887093" if text[match.end():].lstrip().startswith(":") else "#6D7E66"))
            self.setFormat(match.start(), len(match.group()), token)


class ChoiceBox(QComboBox):
    def paintEvent(self,event):
        super().paintEvent(event)
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor("#B4A0C0"),1.4,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
        x,y=self.width()-18,self.height()/2
        painter.drawLine(QPointF(x-4,y-2),QPointF(x,y+2))
        painter.drawLine(QPointF(x,y+2),QPointF(x+4,y-2))


class WorkspaceUI:
    page_meta = (
        ("基本加解密","单分组与逐轮变换","在一个 16 bit 分组中，观察每一步替代、移位和混淆。","lock"),
        ("交叉测试","交换向量 · 检查一致性","交换测试向量，验证独立实现的加密结果与明文还原。","link"),
        ("ASCII 字符串","两字节分组 · 无损还原","将消息分成两字节一组，保留原始长度与每一个密文字节。","text"),
        ("多重加密与攻击","组合密钥 · 中间相遇","组合多把密钥，再用已知明密文对寻找双重加密的密钥。","layers"),
        ("CBC 工作模式","链式依赖 · 篡改实验","用共享 IV 连接多个分组，观察密文修改如何影响解密。","chain"),
    )

    def build_workspace(self):
        self.setStyleSheet(STYLE)
        central=QWidget(); central.setObjectName("Workspace"); self.setCentralWidget(central)
        shell=QHBoxLayout(central); shell.setContentsMargins(0,0,0,0); shell.setSpacing(0)
        sidebar=QFrame(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(230)
        side=QVBoxLayout(sidebar); side.setContentsMargins(16,28,16,19); side.setSpacing(5)
        brand=QHBoxLayout(); brand.setContentsMargins(10,0,0,0); brand.setSpacing(10)
        mark=label("S"); mark.setFixedSize(35,35); mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setStyleSheet("background:#7D6E98;color:white;border-radius:10px;font:600 21px 'Consolas';")
        brand.addWidget(mark); brand.addWidget(label("S-AES","Brand")); brand.addStretch(); side.addLayout(brand)
        side.addSpacing(5); small=label("分组密码 · 交互实验工作台","Tiny"); small.setContentsMargins(10,0,0,0); side.addWidget(small)
        side.addSpacing(34); section=label("实验空间","Section"); section.setContentsMargins(11,0,0,10); side.addWidget(section)
        self.nav_buttons=[]
        for i,(title,note,_,glyph) in enumerate(self.page_meta):
            item=NavButton(title,note,glyph,i,self.select_page); self.nav_buttons.append(item); side.addWidget(item)
        side.addStretch()
        note=QFrame(); note.setObjectName("SidebarNote"); n=QVBoxLayout(note); n.setContentsMargins(14,14,14,14); n.setSpacing(6)
        n.addLayout(row(label("算法规格","FieldLabel"),1,label("附录 D","Tiny")))
        n.addWidget(label("16 bit 分组  ·  2 轮变换","Tiny")); n.addWidget(label("GF(16)  /  x⁴ + x + 1","Tiny"))
        side.addWidget(note); side.addSpacing(10)
        side.addLayout(row(label("信息安全导论","Tiny"),1,label("作业 02","Tiny")))
        shell.addWidget(sidebar)
        main=QVBoxLayout(); main.setContentsMargins(30,23,30,17); main.setSpacing(0); shell.addLayout(main,1)
        self.crumb=label("工作空间  /  单分组密码","Breadcrumb")
        main.addLayout(row(self.crumb,1,label(f"STUDIO {__version__}","Badge"),label("●  本地运行","Online"))); main.addSpacing(14)
        title_row=QHBoxLayout(); self.title_label=label("基本加解密","PageTitle"); self.index_label=label("01 / 05","PageIndex")
        title_row.addWidget(self.title_label); title_row.addSpacing(12); title_row.addWidget(label("S-AES","Badge")); title_row.addStretch(); title_row.addWidget(self.index_label)
        main.addLayout(title_row); main.addSpacing(8)
        self.subtitle_label=label("","Subtitle"); main.addWidget(self.subtitle_label); main.addSpacing(17)
        self.stack=QStackedWidget(); main.addWidget(self.stack,1)
        self.pages=[]
        for build in (self.build_block_page,self.build_cross_page,self.build_ascii_page,self.build_multiple_page,self.build_cbc_page):
            content=QWidget(); content.setObjectName("Workspace"); layout=QVBoxLayout(content); layout.setContentsMargins(1,1,1,7); layout.setSpacing(17)
            build(layout)
            scroll=QScrollArea(); scroll.setFrameShape(QFrame.Shape.NoFrame); scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setStyleSheet("QScrollArea {background:transparent;border:none;}")
            scroll.setWidget(content); self.stack.addWidget(scroll); self.pages.append(content)
        main.addSpacing(13)
        self.status_label=label("就绪 · 输入一个分组开始实验","Status")
        main.addLayout(row(self.status_label,1,label("S-AES LAB  /  PYTHON","Tiny")))
        self.select_page(0)

    def select_page(self,index):
        self.stack.setCurrentIndex(index)
        title,_,description,_=self.page_meta[index]
        self.title_label.setText(title); self.subtitle_label.setText(description)
        self.crumb.setText("工作空间  /  "+title); self.index_label.setText(f"{index+1:02} / 05")
        for i,item in enumerate(self.nav_buttons): item.set_selected(i==index)
        if index == 0 and getattr(self, "current_trace", None) is not None:
            QTimer.singleShot(0, self.ensure_trace_visible)

    def action(self,text,callback,glyph=None,primary=False,ghost=False,on_result=False):
        return button(text,lambda:self.guard(callback),glyph,primary,ghost,on_result)

    def field(self,title,value="",mono=True):
        layout=QVBoxLayout(); layout.setSpacing(7)
        layout.addWidget(label(title,"FieldLabel"))
        edit=QLineEdit(value); edit.setMinimumHeight(41)
        edit.setProperty("mono",mono)
        if mono: edit.setFont(QFont("Consolas",13))
        layout.addWidget(edit)
        return layout,edit

    def editor(self,text="",readonly=False,code=False):
        edit=QPlainTextEdit(text); edit.setReadOnly(readonly); edit.setProperty("readonly",readonly); edit.setProperty("code",code)
        edit.setMinimumHeight(90); edit.setTabChangesFocus(True)
        if code: edit.json_highlighter = JsonHighlighter(edit.document())
        return edit

    def build_block_page(self,layout):
        top=QHBoxLayout(); top.setSpacing(18)
        form=Card("准备一个分组","输入 HEX 或完整 16 位二进制")
        form.body.setContentsMargins(20,17,20,17)
        form.body.setSpacing(12)
        fields=QHBoxLayout(); fields.setSpacing(14)
        p,self.block_input=self.field("明文 / 密文 P · C","6F6B")
        k,self.block_key=self.field("密钥 K","A73B")
        fields.addLayout(p); fields.addLayout(k); form.body.addLayout(fields)
        form.body.addSpacing(1)
        self.encrypt_button=self.action("加密",lambda:self.run_block(False),"lock",True)
        self.decrypt_button=self.action("解密",lambda:self.run_block(True),"unlock")
        self.encrypt_button.setToolTip("加密当前分组 · Ctrl+Enter")
        self.decrypt_button.setToolTip("解密当前分组 · Ctrl+Shift+Enter")
        form.body.addLayout(row(self.encrypt_button,self.decrypt_button,1,self.action("随机",self.random_block,"shuffle",ghost=True)))
        form.body.addWidget(label("支持 0x 前缀与分组二进制，最高位在左。","CardNote"))
        top.addWidget(form,1)
        result=ResultCard(); result.setMinimumWidth(350)
        self.result_card = result
        result.body.setContentsMargins(22,17,22,17)
        result.body.setSpacing(12)
        self.result_tag = label("16 BIT", "ResultTag")
        result.body.addLayout(row(label("运算结果  /  OUTPUT","OutputMeta"),1,self.result_tag))
        self.output_hex=label("0738","Output"); self.output_hex.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        result.body.addWidget(self.output_hex)
        self.output_binary=BinaryStrip(); result.body.addWidget(self.output_binary)
        self.output_caption=label("示例密文 · 加密后生成","OutputMeta")
        self.fill_button = self.action("回填",self.fill_block,"back",on_result=True)
        self.copy_button = self.action("复制",self.copy_block,"copy",on_result=True)
        self.copy_button.setMinimumWidth(92)
        result.body.addLayout(row(self.output_caption,1,self.fill_button,self.copy_button))
        top.addWidget(result,1); layout.addLayout(top)
        trace=Card(); heading=row(label("逐轮状态","CardTitle"),1)
        trace.body.setContentsMargins(20,18,20,18)
        trace.body.setSpacing(10)
        self.key_labels=[label(f"K{i}  ----","KeyChip") for i in range(3)]
        for tone, chip in enumerate(self.key_labels):
            chip.setProperty("tone", str(tone))
            heading.addWidget(chip)
        trace.body.addLayout(heading)
        self.phase_group = QButtonGroup(self)
        self.phase_buttons = []
        filters = QHBoxLayout(); filters.setSpacing(3)
        for index, text in enumerate(("全部步骤", "初始轮", "第 1 轮", "第 2 轮")):
            choice = QPushButton(text)
            choice.setProperty("filter", True)
            choice.setCheckable(True)
            choice.setCursor(Qt.CursorShape.PointingHandCursor)
            choice.setMinimumHeight(30)
            self.phase_group.addButton(choice, index)
            self.phase_buttons.append(choice)
            filters.addWidget(choice)
        self.phase_buttons[0].setChecked(True)
        self.phase_group.idClicked.connect(self.filter_trace)
        filters.addStretch()
        filters.addWidget(label("点选一步，检查状态变化", "CardNote"))
        trace.body.addLayout(filters)
        table_area=QHBoxLayout(); table_area.setSpacing(20)
        self.trace_table=QTableWidget(0,4); self.trace_table.setHorizontalHeaderLabels(("阶段","变换步骤","HEX","BINARY / 16 BIT"))
        self.trace_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.trace_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.trace_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.trace_table.setShowGrid(False); self.trace_table.verticalHeader().hide()
        self.trace_table.verticalHeader().setDefaultSectionSize(30)
        header=self.trace_table.horizontalHeader(); header.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch); header.setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3,QHeaderView.ResizeMode.ResizeToContents)
        self.trace_table.setMinimumHeight(240); self.trace_table.itemSelectionChanged.connect(self.show_selected_state)
        table_area.addWidget(self.trace_table,1)
        inspect=QVBoxLayout(); inspect.setSpacing(6)
        self.state_step = label("09 / 09", "CardNote")
        self.state_hex = label("0738", "StepValue")
        inspect.addLayout(row(self.state_hex,1,self.state_step))
        self.state_matrix=StateMatrix(); inspect.addWidget(self.state_matrix,0,Qt.AlignmentFlag.AlignHCenter)
        self.state_matrix.setToolTip("着色单元格表示与上一步不同；s00、s01、s10、s11 为状态矩阵坐标。")
        self.state_caption=label("点击任一行，检查中间状态。","CardNote",True); self.state_caption.setFixedWidth(152)
        inspect.addWidget(self.state_caption)
        self.prev_step_button = self.action("上一步", lambda:self.move_trace(-1), ghost=True)
        self.next_step_button = self.action("下一步", lambda:self.move_trace(1), ghost=True)
        self.prev_step_button.setToolTip("上一步 · Alt+←")
        self.next_step_button.setToolTip("下一步 · Alt+→")
        self.prev_step_button.setMinimumWidth(66)
        self.next_step_button.setMinimumWidth(66)
        for control in (self.prev_step_button,self.next_step_button):
            control.setMinimumHeight(28)
            control.setMaximumHeight(30)
        inspect.addLayout(row(self.prev_step_button,self.next_step_button,spacing=2))
        inspect.addStretch(); table_area.addLayout(inspect)
        trace.body.addLayout(table_area,1)
        layout.addWidget(trace,1)

    def build_cross_page(self,layout):
        panels=QHBoxLayout(); panels.setSpacing(18)
        left=Card("交换测试向量","包含边界值与随机样本")
        left.body.addLayout(row(self.action("生成向量",self.generate_cross,"grid",True),1,self.action("导出",lambda:self.save_editor(self.cross_text,"cross_vectors.json"),"export")))
        self.cross_text=self.editor(code=True); left.body.addWidget(self.cross_text,1)
        left.body.addWidget(label("P / K / C 以 4 位 HEX 交换，双方采用相同算法规格。","CardNote",True))
        panels.addWidget(left,1)
        right=Card("一致性验证","同时检查密文相等与明文还原")
        right.body.addLayout(row(self.action("导入对方文件",lambda:self.load_editor(self.cross_text),"import"),1,self.action("开始验证",self.verify_cross,"check",True)))
        self.cross_summary=label("等待对方测试向量","Summary"); right.body.addWidget(self.cross_summary)
        self.cross_result=self.editor(readonly=True); right.body.addWidget(self.cross_result,1)
        right.body.addWidget(label("验证自己生成的向量属于自检，不能替代另一小组互测。","CardNote",True))
        panels.addWidget(right,1); layout.addLayout(panels,1)

    def build_ascii_page(self,layout):
        panels=QHBoxLayout(); panels.setSpacing(18)
        plain=Card("明文工作区","ASCII / 每个分组 2 Bytes")
        key,self.ascii_key=self.field("密钥 K","A73B"); plain.body.addLayout(key)
        self.ascii_plain=self.editor("Hello, S-AES!"); plain.body.addWidget(self.ascii_plain,1)
        self.ascii_count = label("13 Bytes · 7 组 · 末组补 1 字节", "CardNote")
        plain.body.addWidget(self.ascii_count)
        plain.body.addLayout(row(self.action("加密",self.encrypt_ascii_gui,"lock",True),self.action("解密",self.decrypt_ascii_gui,"unlock"),1))
        panels.addWidget(plain,1)
        packet=Card("密文包","保留原始长度，可跨会话导入")
        packet.body.addLayout(row(self.action("导入",lambda:self.load_editor(self.ascii_packet),"import"),self.action("导出",lambda:self.save_editor(self.ascii_packet,"ascii_cipher.json"),"export"),1,label("JSON","Badge")))
        self.ascii_packet=self.editor(code=True); packet.body.addWidget(self.ascii_packet,1)
        panels.addWidget(packet,1); layout.addLayout(panels,1)
        preview=Card("密文字节","不可打印字节显示为 \\xHH，原始数据不会丢失")
        self.ascii_preview=label("加密后在这里查看实际密文字节。","Preview",True); self.ascii_preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        preview.body.addWidget(self.ascii_preview); layout.addWidget(preview)

    def build_multiple_page(self,layout):
        panels=QHBoxLayout(); panels.setSpacing(18)
        form=Card("组合密钥","双重 EE / 三重 EEE")
        form.setMaximumWidth(390)
        self.multi_mode=ChoiceBox(); self.multi_mode.addItems(("双重 / 32 bit","三重 / 48 bit","三重 / 32 bit")); self.multi_mode.currentIndexChanged.connect(self.multi_mode_changed)
        form.body.addWidget(label("加密模式","FieldLabel")); form.body.addWidget(self.multi_mode)
        key,self.multi_key=self.field("组合密钥 K1 || K2 [ || K3 ]","1F2E3D4C"); form.body.addLayout(key)
        data,self.multi_input=self.field("明文 / 密文分组","6F6B"); form.body.addLayout(data)
        form.body.addLayout(row(self.action("加密",lambda:self.run_multiple(False),"lock",True),self.action("解密",lambda:self.run_multiple(True),"unlock"),1))
        self.multi_output=label("等待运算","Summary",True); form.body.addWidget(self.multi_output)
        form.body.addLayout(row(self.action("结果回填",self.fill_multiple,"back",ghost=True),1)); form.body.addStretch()
        form.body.addWidget(label("三重 / 32 bit 采用 K1 → K2 → K1。\n模式显式指定，保留前导零密钥。","CardNote",True))
        panels.addWidget(form,4)
        attack=Card("中间相遇攻击","从已知明密文对恢复双重加密密钥")
        attack.body.addLayout(row(label("每行 P C · 均为 4 位 HEX","FieldLabel"),1,self.action("载入示例",self.load_attack_demo,"grid",ghost=True)))
        self.attack_pairs=self.editor(); self.attack_pairs.setMaximumHeight(125); attack.body.addWidget(self.attack_pairs)
        self.attack_start_button=self.action("开始完整搜索",self.start_attack,"play",True)
        self.attack_cancel_button=self.action("取消",self.attack_cancel.set,"stop"); self.attack_cancel_button.setEnabled(False)
        attack.body.addLayout(row(self.attack_start_button,self.attack_cancel_button,1,self.action("导出候选",self.save_candidates,"export",ghost=True)))
        self.attack_progress=QProgressBar(); self.attack_progress.setRange(0,131072); self.attack_progress.setValue(0); self.attack_progress.setTextVisible(False); attack.body.addWidget(self.attack_progress)
        self.attack_status=label("完整枚举 K1、K2 各 65,536 个值","CardNote"); attack.body.addWidget(self.attack_status)
        self.attack_result=self.editor("建议使用三组不同明文，过滤单对产生的碰撞。",readonly=True); attack.body.addWidget(self.attack_result,1)
        panels.addWidget(attack,6); layout.addLayout(panels,1)

    def build_cbc_page(self,layout):
        panels=QHBoxLayout(); panels.setSpacing(18)
        plain=Card("消息与共享向量","CBC / 连接多个分组")
        fields=QHBoxLayout(); fields.setSpacing(12)
        key,self.cbc_key=self.field("密钥 K","A73B"); iv,self.cbc_iv=self.field("共享 IV","")
        fields.addLayout(key); fields.addLayout(iv); plain.body.addLayout(fields)
        self.cbc_plain=self.editor("Hello, S-AES CBC mode!"); self.cbc_plain.setMinimumHeight(85); plain.body.addWidget(self.cbc_plain,1)
        self.cbc_count = label("22 Bytes · 11 组", "CardNote")
        plain.body.addWidget(self.cbc_count)
        plain.body.addLayout(row(self.action("加密",self.encrypt_cbc_gui,"lock",True),self.action("解密",self.decrypt_cbc_gui,"unlock"),1,self.action("随机 IV",self.random_iv,"shuffle",ghost=True)))
        panels.addWidget(plain,1)
        packet=Card("密文包与 IV","解密时自动采用包内共享 IV")
        packet.body.addLayout(row(self.action("导入",lambda:self.load_editor(self.cbc_packet),"import"),self.action("导出",lambda:self.save_editor(self.cbc_packet,"cbc_cipher.json"),"export"),1,label("JSON","Badge")))
        self.cbc_packet=self.editor(code=True); packet.body.addWidget(self.cbc_packet,1); panels.addWidget(packet,1)
        layout.addLayout(panels,3)
        tamper=Card("篡改实验","修改 Ci，比较 Pi 与下一分组的变化")
        controls=QHBoxLayout(); controls.setSpacing(12)
        controls.addWidget(label("分组 #","FieldLabel")); self.tamper_index=QLineEdit("1"); self.tamper_index.setFixedWidth(52); controls.addWidget(self.tamper_index)
        self.tamper_mode=ChoiceBox(); self.tamper_mode.addItems(("异或翻转","替换分组")); self.tamper_mode.setFixedWidth(120); controls.addWidget(self.tamper_mode)
        self.tamper_value=QLineEdit("0001"); self.tamper_value.setFixedWidth(85); self.tamper_value.setFont(QFont("Consolas",11)); controls.addWidget(self.tamper_value)
        controls.addWidget(self.action("对比解密",self.compare_tamper,"chain",True)); controls.addStretch()
        tamper.body.addLayout(controls)
        self.cbc_comparison=self.editor("先加密一条消息，再选择一个密文分组进行修改。",readonly=True); self.cbc_comparison.setMinimumHeight(105); tamper.body.addWidget(self.cbc_comparison,1)
        layout.addWidget(tamper,2)
