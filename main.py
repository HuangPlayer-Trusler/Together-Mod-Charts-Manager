import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor
from adofai_viewer.main_window import MainWindow   # 包名.模块名

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor('#1e1e2e'))
    palette.setColor(QPalette.WindowText,      QColor('#cdd6f4'))
    palette.setColor(QPalette.Base,            QColor('#181825'))
    palette.setColor(QPalette.AlternateBase,   QColor('#1e1e2e'))
    palette.setColor(QPalette.Text,            QColor('#cdd6f4'))
    palette.setColor(QPalette.Button,          QColor('#313244'))
    palette.setColor(QPalette.ButtonText,      QColor('#cdd6f4'))
    palette.setColor(QPalette.Highlight,       QColor('#45475a'))
    palette.setColor(QPalette.HighlightedText, QColor('#cdd6f4'))
    app.setPalette(palette)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()