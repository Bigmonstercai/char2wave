#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
# import random
from PyQt4 import QtGui, QtCore
import re
import time

# 定义全局变量
timeScale = 1                                                                                           # 单位时间，单位为ns
netWidth = 20                                                                                           # 单元格宽度，单位为px，1格对应1单位时间
netHeight = 50                                                                                          # 单元格高度，单位为px，1行对应一个信号
scaleLength = 5                                                                                         # 刻度线长度，单位为px
originY = 20                                                                                            # 第一个波形上边缘的Y坐标
originX = 100                                                                                           # 波形起始位置的X坐标
hasGlobal = 0                                                                                           # 指示是否已经有全局时钟信号
signals = []                                                                                            # 全部信号名称列表
clocks = {}                                                                                             # 全部时钟频率
defaultFont = QtGui.QFont('DejaVu Sans Mono', 12)                                                       # 默认字体
defaultPen = QtGui.QPen(QtGui.QColor(0, 0, 0))                                                          # 默认线型


class MainWindow(QtGui.QMainWindow):

    # 生成界面
    def __init__(self):
        global timeScale
        global netWidth
        global netHeight
        global scaleLength
        global originY
        global originX
        global hasGlobal
        global signals
        global defaultFont
        QtGui.QMainWindow.__init__(self)

        self.resize(800, 600)
        self.setWindowTitle('char2wave')

        exit = QtGui.QAction('Exit', self)
        exit.setShortcut('Ctrl+Q')
        exit.setStatusTip('Exit application')
        self.connect(exit, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))

        save = QtGui.QAction('Save', self)
        save.setShortcut('Ctrl+S')
        save.setStatusTip('Save File')
        self.connect(save, QtCore.SIGNAL('triggered()'), self.saveFile)

        openf = QtGui.QAction('Open', self)
        openf.setShortcut('Ctrl+O')
        openf.setStatusTip('Open File')
        self.connect(openf, QtCore.SIGNAL('triggered()'), self.openFile)

        self.statusBar()

        menubar = self.menuBar()
        file = menubar.addMenu('&File')
        file.addAction(openf)
        file.addAction(save)
        file.addAction(exit)

        self.view = QtGui.QGraphicsView()
        self.view.setToolTip(u'语法说明：\n1.每行输入代表一个信号\n2.每个信号的输入格式为“信号名(信号属性):信号波形描述”\n3.信号属性各个属性使用英文逗号隔开，属性无先后顺序，信号属性可以为空，但是括号必须保留，此时信号为非同步普通信号\n\
4.当属性中包含“clk”时表示当前信号为一个时钟信号，否则为普通信号\n5.时钟信号的表示方式为“时钟名(clk,其他属性):时钟频率”,如：\n\tclk(clk,global):50MHz\n\tglobal属性指示当前时钟信号为全局时钟，即坐标轴一个格代表\
该时钟信号的半个周期\n6.普通信号分为同步信号和非同步信号，同步信号需指定同步时钟，其波形描述中每个符号对应该时钟一个周期；非同步信号波形描述中每个符号对应坐标轴的一格\n7.同步信号的表示方式为“信号名(syn:\
同步时钟名称,其他属性):信号波形描述”\n8.所有信号都有上升时间及下降时间两个属性,分别用rt和ft表示，单位为ns，若不写则默认为0,如:\n\tclk(clk,rt:1):50MHz\n\tsignal(rt:2,ft:1):-_-XZZZ\n9.普通信号波形描述符号：\n\t-\t高电平\n\
\t_\t低电平\n\tX\t未知信号\n\tZ\t高阻信号\n\t=\t信号向量\n\t<\t信号向量左边缘\n\t>\t信号向量右边缘\n\t~\t省略号\n10.可以使用*绘制重复波形,如:\n\t(-_-)*5\n\t=*10')
        self.plain = QtGui.QPlainTextEdit()

        self.vbox = QtGui.QVBoxLayout()
        self.vbox.addWidget(self.view)
        self.vbox.addWidget(self.plain)

        self.centralWidget = QtGui.QWidget(self)
        self.centralWidget.setLayout(self.vbox)
        self.setCentralWidget(self.centralWidget)

        self.scene = QtGui.QGraphicsScene(0, 0, 800, 400)
        # self.drawScale()
        text = self.scene.addText(u"欢迎测试char2wave!\n当前版本：\n\t1.可绘制时钟信号、单个信号及信号向量\n\t2.可定义全局时钟信号以改变单位时间\n\t3.可将输入保存为c2w格式文件，可载入已保存c2w文件\n\
暂时不能：\n\t1.让信号向量显示具体值\n\t2.对信号进行标注\n\t3.将绘制出的波形保存为图片\n\n\n无论何时，你都可以将鼠标移到这里查看详细语法", defaultFont)
        text.setPos(0, originY)

        self.view.setScene(self.scene)
        self.view.centerOn(0, 0)
        self.view.show()

        self.connect(self.plain, QtCore.SIGNAL("textChanged()"), self.updateScene)

    # 更新场景
    def updateScene(self):
        global timeScale
        global netWidth
        global netHeight
        global scaleLength
        global originY
        global originX
        global hasGlobal
        global signals
        global clocks
        global defaultFont
        self.scene.clear()
        signals = []
        clocks = {}
        hasGlobal = 0
        self.drawScale()
        Y = originY
        texts = str(self.plain.toPlainText().toUtf8())
        texts = texts.split('\n')
        for text in texts:
            try:
                signal = wave(text, self.scene)
                if signal.warning:
                    signal_show = signal.warning
                elif signal.type == 'clock':
                    signal.drawClk(self.scene, Y)
                else:
                    signal.drawSig(self.scene, Y)

                if signal.warning is False:
                    signals.append(signal.name)
                else:
                    signal_show.setPos(0, Y)
                Y += netHeight
                if Y >= 0.8 * self.scene.height():
                    self.scene.setSceneRect(0, 0, self.scene.width(), int(self.scene.height() * 1.2))
            except Exception as e:
                print e
                pass
        scale_show = self.scene.addText(u'%.8gns/格' % timeScale)
        scale_show.setPos(0, 0)

    # 画刻度线
    def drawScale(self):
        global originX
        for i in range(originX, int(self.scene.width()), netWidth):
            self.scene.addLine(i, 0, i, scaleLength, QtGui.QColor(0, 0, 0))

    # 打字动画
    def typeAnimation(self, text, posX=0, posY=0, font=defaultFont):
        oriX = posX
        for c in text:
            if c == '\n':
                posY += 20
                posX = oriX
            else:
                text = self.scene.addText(c, font)
                text.setPos(posX, posY)
                posX += 13
                self.view.show()
                time.sleep(0.8)

    # 保存文件
    def saveFile(self):
        filename = QtGui.QFileDialog.getSaveFileName(self, "Save File", "./untitled.c2w", "char2wave File(*.c2w)")
        if filename != '':
            if filename[-4:] != '.c2w':
                filename += '.c2w'
            f = open(filename, 'w')
            content = self.plain.toPlainText().toUtf8()
            f.write(content)
            f.close()

    # 打开文件
    def openFile(self):
        filename = QtGui.QFileDialog.getOpenFileName(self, "Open File", "", "char2wave File(*.c2w)")
        if filename != '':
            f = open(filename, 'r')
            content = f.read()
            self.plain.setPlainText(content.decode('utf8'))
            f.close()


class wave(object):

    def __init__(self, text, scene):
        global timeScale
        global netWidth
        global netHeight
        global scaleLength
        global originY
        global originX
        global hasGlobal
        global signals
        global clocks
        global defaultFont
        self.warning = False
        text_re = re.match('(.+):(.+)', text)                                                                                                           # 检查该行输入是否符合规范
        if text_re:                                                                                                                                     # 如果符合规范则进行分析
            proper = text_re.group(1)                                                                                                                   # 将信号名及信号属性保存为proper变量
            self.waveform = text_re.group(2).decode('utf8')                                                                                             # 将信号波形描述保存为self.waveform变量
            proper = re.match('(.+)\((.*)\)', proper)                                                                                                   # 对信号名及信号属性的格式进行检查
            if proper:                                                                                                                                  # 如果信号名及信号属性符合规范则继续进行解析
                self.name = proper.group(1).decode('utf8')                                                                                              # 将信号名提取出来保存
                if self.name in signals:                                                                                                                # 如果已存在同名信号则输出警告
                    self.warning = scene.addText(('There has already had a signal named %s!' % self.name).decode('utf8'), defaultFont)
                proper_all = proper.group(2)                                                                                                            # 将全部属性保存
                proper = proper_all.split(',')                                                                                                          # 不同属性用逗号分隔
                if proper_all == '':                                                                                                                    # 属性为空的信号视为非同步普通信号
                    self.type = 'signal'
                    self.syn = 0
                    self.width = netWidth
                elif 'clk' in proper:                                                                                                                   # 属性包含'clk'视为时钟信号
                    self.type = 'clock'
                    waveform_re = re.search('(\d+(.\d+)?)(\w?)Hz', self.waveform)                                                              # 对时钟信号的波形描述匹配，提取出频率和初始电平
                    havef = True
                    if waveform_re:
                        if waveform_re.group(3) == '':
                            self.f = float(waveform_re.group(1))
                        elif waveform_re.group(3) == 'K' or waveform_re.group(3) == 'k':
                            self.f = float(waveform_re.group(1)) * (10**3)
                        elif waveform_re.group(3) == 'M' or waveform_re.group(3) == 'm':
                            self.f = float(waveform_re.group(1)) * (10**6)
                        elif waveform_re.group(3) == 'G' or waveform_re.group(3) == 'g':
                            self.f = float(waveform_re.group(1)) * (10**9)
                        elif waveform_re.group(3) == 'T' or waveform_re.group(3) == 't':
                            self.f = float(waveform_re.group(1)) * (10**12)
                        elif waveform_re.group(3) == 'P' or waveform_re.group(3) == 'p':
                            self.f = float(waveform_re.group(1)) * (10**15)
                        else:                                                                                                                           # 如果频率表述不正确则输出警告
                            havef = False
                            self.warning = scene.addText(('Frequency of clock' + self.name + 'has something wrong!').decode('utf8'), defaultFont)
                        clocks[self.name] = self.f
                        if 'global' in proper and havef:                                                                                                # 如果是全局时钟，则时间轴一格对应该时钟半个周期
                            if hasGlobal == 1:                                                                                                          # 如果已存在全局时钟则输出警告
                                self.warning = scene.addText(('There has already had a global clock!').decode('utf8'), defaultFont)
                            else:
                                timeScale = (10**9) / (2.0 * self.f)
                                hasGlobal = 1
                                self.width = netWidth
                        else:
                            self.width = (10**9) * netWidth / (2 * self.f * timeScale)
                    else:                                                                                                                               # 如果时钟信号的波形描述不符合规范则输出警告
                        self.warning = scene.addText(('You should input "frequency,l or h" after ":" for a clock!').decode('utf8'), defaultFont)
                else:                                                                                                                                   # 不包含clk属性即视为普通信号
                    self.type = 'signal'
                    syn = re.search('(s:)([^,]+)', proper_all)                                                                                          # 检查是否属于同步信号
                    if syn:                                                                                                                             # 如果是的话self.syn为1，self.synclk为对应的时钟信号
                        self.syn = 1                                                                                                                    # 否则self.syn为0
                        self.syn_clk = syn.group(2).decode('utf8')
                        if clocks.get(self.syn_clk):
                            self.width = (10**9) * netWidth / (clocks[self.syn_clk] * timeScale)
                        else:
                            self.warning = scene.addText(('No clock named "' + self.syn_clk + '" exits!').decode('utf8'), defaultFont)
                    else:
                        self.syn = 0
                        self.width = netWidth
                raiseTime = re.search('rt:(\d+)', proper_all)                                                                                           # 检查属性中是否设置了上升时间，有的话将时间保存，否则为0
                if raiseTime:
                    self.rt = int(raiseTime.group(1))
                else:
                    self.rt = 0
                fallTime = re.search('ft:(\d+)', proper_all)                                                                                            # 检查属性中是否设置了下降时间，有的话将时间保存，否则为0
                if fallTime:
                    self.ft = int(fallTime.group(1))
                else:
                    self.ft = 0
                if '=' in self.waveform:                                                                                                                # 信号向量的上升下降时间按二者的最大值计算
                    self.rt = max(self.rt, self.ft)
                    self.ft = max(self.rt, self.ft)
            else:                                                                                                                                       # 如果信号名及信号属性不符合规范则输出警告
                self.warning = scene.addText(('You should input "name(proper)" before ":"!').decode('utf8'), defaultFont)
        else:                                                                                                                                           # 如果不符合规范则输出警告
            self.warning = scene.addText(('"' + text + '" is an invalid input!').decode('utf8'), defaultFont)

    def drawLow(self, scene, X, Y):
        global timeScale
        global netWidth
        global netHeight
        global scaleLength
        global originY
        global originX
        global hasGlobal
        global signals
        global defaultFont
        global defaultPen
        leftB = (self.ft * netWidth) / (2 * timeScale)
        rightB = (self.rt * netWidth) / (2 * timeScale)
        scene.addLine(int(X + leftB), int(Y + 0.8 * netHeight), int(X + self.width - rightB), int(Y + 0.8 * netHeight), defaultPen)

    def drawHigh(self, scene, X, Y):
        global timeScale
        global netWidth
        global netHeight
        global scaleLength
        global originY
        global originX
        global hasGlobal
        global signals
        global defaultFont
        global defaultPen
        rightB = (self.ft * netWidth) / (2 * timeScale)
        leftB = (self.rt * netWidth) / (2 * timeScale)
        scene.addLine(int(X + leftB), int(Y + 0.2 * netHeight), int(X + self.width - rightB), int(Y + 0.2 * netHeight), defaultPen)

    def drawXZ(self, scene, X, Y, type):
        global timeScale
        global netWidth
        global netHeight
        global scaleLength
        global originY
        global originX
        global hasGlobal
        global signals
        global defaultFont
        global defaultPen
        if type == 'X':
            scene.addLine(int(X), int(Y + 0.5 * netHeight), int(X + self.width), int(Y + 0.5 * netHeight), QtGui.QPen(QtGui.QColor(255, 0, 0)))
        elif type == 'Z':
            scene.addLine(int(X), int(Y + 0.5 * netHeight), int(X + self.width), int(Y + 0.5 * netHeight), QtGui.QPen(QtGui.QColor(0, 0, 255)))

    def drawBlank(self, scene, X, Y, type):
        global timeScale
        global netWidth
        global netHeight
        global scaleLength
        global originY
        global originX
        global hasGlobal
        global signals
        global defaultFont
        global defaultPen

        FB = (self.ft * netWidth) / (2 * timeScale)
        RB = (self.rt * netWidth) / (2 * timeScale)

        if type == 'HHR':
            scene.addLine(int(X - max(FB, RB)), int(Y + 0.2 * netHeight), int(X), int(Y + 0.2 * netHeight), defaultPen)
        elif type == 'HHL':
            scene.addLine(int(X), int(Y + 0.2 * netHeight), int(X + max(FB, RB)), int(Y + 0.2 * netHeight), defaultPen)
        elif type == 'LLR':
            scene.addLine(int(X - max(FB, RB)), int(Y + 0.8 * netHeight), int(X), int(Y + 0.8 * netHeight), defaultPen)
        elif type == 'LLL':
            scene.addLine(int(X), int(Y + 0.8 * netHeight), int(X + max(FB, RB)), int(Y + 0.8 * netHeight), defaultPen)
        elif type == 'HXR':
            scene.addLine(int(X - FB), int(Y + 0.2 * netHeight), int(X), int(Y + 0.5 * netHeight), defaultPen)
        elif type == 'XHL':
            scene.addLine(int(X), int(Y + 0.5 * netHeight), int(X + RB), int(Y + 0.2 * netHeight), defaultPen)
        elif type == 'LXR':
            scene.addLine(int(X - RB), int(Y + 0.8 * netHeight), int(X), int(Y + 0.5 * netHeight), defaultPen)
        elif type == 'XLL':
            scene.addLine(int(X), int(Y + 0.5 * netHeight), int(X + FB), int(Y + 0.8 * netHeight), defaultPen)

    def drawClk(self, scene, Y):
        global timeScale
        global netWidth
        global netHeight
        global scaleLength
        global originY
        global originX
        global hasGlobal
        global signals
        global defaultFont
        global defaultPen

        name_show = scene.addText(self.name, defaultFont)
        name_show.setPos(0, Y + 0.3 * netHeight)
        H = 1
        for X in range(originX, int(scene.width()), int(self.width)):                                                   # 当时钟信号频率比全局时钟信号高20倍以上时，会导致int(self.width)为0而出错
            if H == 1:
                self.drawBlank(scene, X, Y, 'LXR')
                self.drawBlank(scene, X, Y, 'XHL')
                self.drawHigh(scene, X, Y)
            else:
                self.drawBlank(scene, X, Y, 'HXR')
                self.drawBlank(scene, X, Y, 'XLL')
                self.drawLow(scene, X, Y)
            H = 1 - H

    def drawSig(self, scene, Y):
        global timeScale
        global netWidth
        global netHeight
        global scaleLength
        global originY
        global originX
        global hasGlobal
        global signals
        global defaultFont
        global defaultPen

        while True:
            wave_re = re.search('\((.+)\)\*(\d+)', self.waveform)
            if wave_re:
                pass
            else:
                wave_re = re.search('([-_=XZ~])\*(\d+)', self.waveform)
            if wave_re:
                s = ''
                n = int(wave_re.group(2))
                for i in range(n):
                    s += wave_re.group(1)
                self.waveform = self.waveform.replace(wave_re.group(0), s)
            else:
                break

        name_show = scene.addText(self.name, defaultFont)
        name_show.setPos(0, Y + 0.3 * netHeight)
        X = originX
        pre = ''
        for c in self.waveform:
            if c == '-' and (pre == '' or pre == 'X' or pre == 'Z'):
                self.drawBlank(scene, X, Y, 'XHL')
                self.drawHigh(scene, X, Y)
            elif c == '-' and pre == '-':
                self.drawBlank(scene, X, Y, 'HHR')
                self.drawBlank(scene, X, Y, 'HHL')
                self.drawHigh(scene, X, Y)
            elif c == '-' and pre == '_':
                self.drawBlank(scene, X, Y, 'LXR')
                self.drawBlank(scene, X, Y, 'XHL')
                self.drawHigh(scene, X, Y)
            elif c == '-' and pre == '~':
                self.drawBlank(scene, X, Y, 'HHL')
                self.drawHigh(scene, X, Y)
            elif c == '_' and (pre == '' or pre == 'X' or pre == 'Z'):
                self.drawBlank(scene, X, Y, 'XLL')
                self.drawLow(scene, X, Y)
            elif c == '_' and pre == '-':
                self.drawBlank(scene, X, Y, 'HXR')
                self.drawBlank(scene, X, Y, 'XLL')
                self.drawLow(scene, X, Y)
            elif c == '_' and pre == '_':
                self.drawBlank(scene, X, Y, 'LLR')
                self.drawBlank(scene, X, Y, 'LLL')
                self.drawLow(scene, X, Y)
            elif c == '_' and pre == '~':
                self.drawBlank(scene, X, Y, 'LLL')
                self.drawLow(scene, X, Y)
            elif c == 'X' and (pre == '' or pre == 'X' or pre == 'Z' or pre == '~'):
                self.drawXZ(scene, X, Y, 'X')
            elif c == 'X' and pre == '-':
                self.drawBlank(scene, X, Y, 'HXR')
                self.drawXZ(scene, X, Y, 'X')
            elif c == 'X' and pre == '_':
                self.drawBlank(scene, X, Y, 'LXR')
                self.drawXZ(scene, X, Y, 'X')
            elif c == 'X' and pre == '=':
                self.drawBlank(scene, X, Y, 'HXR')
                self.drawBlank(scene, X, Y, 'LXR')
                self.drawXZ(scene, X, Y, 'X')
            elif c == 'Z' and (pre == '' or pre == 'X' or pre == 'Z' or pre == '~'):
                self.drawXZ(scene, X, Y, 'Z')
            elif c == 'Z' and pre == '-':
                self.drawBlank(scene, X, Y, 'HXR')
                self.drawXZ(scene, X, Y, 'Z')
            elif c == 'Z' and pre == '_':
                self.drawBlank(scene, X, Y, 'LXR')
                self.drawXZ(scene, X, Y, 'Z')
            elif c == 'Z' and pre == '=':
                self.drawBlank(scene, X, Y, 'HXR')
                self.drawBlank(scene, X, Y, 'LXR')
                self.drawXZ(scene, X, Y, 'Z')
            elif c == '=' and (pre == '' or pre == 'X' or pre == 'Z'):
                self.drawBlank(scene, X, Y, 'XHL')
                self.drawBlank(scene, X, Y, 'XLL')
                self.drawHigh(scene, X, Y)
                self.drawLow(scene, X, Y)
            elif c == '=' and pre == '=':
                self.drawBlank(scene, X, Y, 'HHR')
                self.drawBlank(scene, X, Y, 'LLR')
                self.drawBlank(scene, X, Y, 'HHL')
                self.drawBlank(scene, X, Y, 'LLL')
                self.drawHigh(scene, X, Y)
                self.drawLow(scene, X, Y)
            elif c == '=' and pre == '<':
                self.drawHigh(scene, X, Y)
                self.drawLow(scene, X, Y)
            elif c == '=' and pre == '~':
                self.drawBlank(scene, X, Y, 'HHL')
                self.drawBlank(scene, X, Y, 'LLL')
                self.drawHigh(scene, X, Y)
                self.drawLow(scene, X, Y)
            elif c == '>':
                self.drawBlank(scene, X, Y, 'HXR')
                self.drawBlank(scene, X, Y, 'LXR')
                X -= self.width
            elif c == '<':
                self.drawBlank(scene, X, Y, 'XHL')
                self.drawBlank(scene, X, Y, 'XLL')
                X -= self.width
            elif c == '~':
                omi = scene.addText(u'……', defaultFont)
                omi.setPos(X, Y + 0.3 * netWidth)
            X += self.width
            if X >= 0.8 * scene.width():
                scene.setSceneRect(0, 0, int(scene.width() * 1.2), scene.height())
            pre = c


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    main = MainWindow()
    main.show()
    sys.exit(app.exec_())
