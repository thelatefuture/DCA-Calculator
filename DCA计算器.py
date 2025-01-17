import sys
from PyQt5.QtCore import (
    pyqtSlot, QSettings, QSize, QPoint, Qt
)
from PyQt5.QtGui import (
    QPalette, QColor
)
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QFormLayout, QGroupBox,
    QLabel, QSpinBox, QDoubleSpinBox, QTableWidget, QTableWidgetItem,
    QSizePolicy, QHeaderView
)


class InvestmentCalculator(QWidget):
    def __init__(self):
        super().__init__()
        # 使用 QSettings 记忆上次使用时的窗口和控件状态
        self.settings = QSettings('MyApp', 'InvestmentCalculator')

        # 初始化界面
        self.initUI()

    def initUI(self):
        """
        设置窗口、暗色主题、布局和控件。
        """
        # 窗口标题
        self.setWindowTitle('投资计算器（DCA）')

        # ===== 样式表：暗色主题 + 去除图标，仅保留上下按钮可点击区域 =====
        self.setStyleSheet("""
            QWidget {
                background-color: #2B2B2B;
                color: #EAEAEA;
            }
            QSpinBox, QDoubleSpinBox, QLineEdit, QTableWidget {
                background-color: #3B3B3B;
                border: 1px solid #5A5A5A;
                selection-background-color: #555555;
            }
            /* 去掉原先的箭头图标，仅保留点击区域 */
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow,
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                image: none;
                width: 0;
                height: 0;
            }
            /* 上下按钮自身可见，使用深色区块做区分 */
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: top right;
                width: 18px;
                border-left: 1px solid #5A5A5A;
                background-color: #4A4A4A;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: bottom right;
                width: 18px;
                border-left: 1px solid #5A5A5A;
                background-color: #4A4A4A;
            }
            /* 表格选中行 */
            QTableWidget::item:selected {
                background-color: #555555;
            }
        """)

        # ========== 主布局（垂直） ==========
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        # ========== 参数设置分组框 ==========
        group_input = QGroupBox("参数设置")
        form_layout = QFormLayout()
        group_input.setLayout(form_layout)

        # --- 初始订单值 ---
        self.order_value_input = QSpinBox()
        self.order_value_input.setRange(0, 1000000)
        self.order_value_input.setValue(self.settings.value('order_value', 100, type=int))
        # 最小步进单位改为 50
        self.order_value_input.setSingleStep(50)
        self.order_value_input.valueChanged.connect(self.updateResult)
        form_layout.addRow("初始订单值：", self.order_value_input)

        # --- DCA次数 ---
        self.dca_count_input = QSpinBox()
        self.dca_count_input.setRange(1, 100)
        self.dca_count_input.setValue(self.settings.value('dca_count', 6, type=int))
        self.dca_count_input.valueChanged.connect(self.updateResult)
        form_layout.addRow("DCA次数：", self.dca_count_input)

        # --- DCA乘数 ---
        self.dca_multiplier_input = QDoubleSpinBox()
        self.dca_multiplier_input.setRange(0.1, 10.0)
        self.dca_multiplier_input.setSingleStep(0.1)
        self.dca_multiplier_input.setValue(self.settings.value('dca_multiplier', 1.5, type=float))
        self.dca_multiplier_input.valueChanged.connect(self.updateResult)
        form_layout.addRow("DCA乘数：", self.dca_multiplier_input)

        # --- 杠杆倍数 ---
        self.leverage_input = QDoubleSpinBox()
        self.leverage_input.setRange(1, 125)
        self.leverage_input.setSingleStep(1)
        self.leverage_input.setValue(self.settings.value('leverage', 5, type=float))
        self.leverage_input.valueChanged.connect(self.updateResult)
        form_layout.addRow("杠杆倍数：", self.leverage_input)

        main_layout.addWidget(group_input)

        # ========== 结果查看分组框 ==========
        group_result = QGroupBox("结果查看")
        vbox_result = QVBoxLayout()
        group_result.setLayout(vbox_result)

        # --- 显示杠杆金额 + 实际金额 ---
        self.result_label = QLabel("杠杆金额将显示在这里")
        self.result_label.setFixedHeight(30)
        self.result_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        vbox_result.addWidget(self.result_label)

        # --- 表格控件（3列：步骤、杠杆金额、实际金额） ---
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        # 将第二列的标题改为“杠杆金额”
        self.table.setHorizontalHeaderLabels(["步骤", "杠杆金额", "实际金额"])

        # 使列宽随窗口变化，避免右侧空白
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        vbox_result.addWidget(self.table)
        main_layout.addWidget(group_result)

        # 初始化计算并恢复窗口状态
        self.updateResult()
        self.initWindowPositionAndSize()

    def initWindowPositionAndSize(self):
        """
        从QSettings中读取并恢复窗口大小和位置，如果没有则使用默认值。
        """
        saved_size = self.settings.value('window_size', QSize(420, 480), type=QSize)
        saved_pos = self.settings.value('window_position', QPoint(100, 100), type=QPoint)

        self.resize(saved_size)
        self.move(saved_pos)

    @pyqtSlot()
    def updateResult(self):
        """
        计算DCA每一步，以及“实际金额 = 累计投资 ÷ 杠杆倍数”，更新表格和顶部标签。
        其中：
         - 第1行名称“初始金额”
         - 后续行依次显示为“DCA1”、“DCA2”、“DCA3”...
         - 第二列显示为“杠杆金额”（实则原先的累计投资），
           第三列为“实际金额 = 杠杆金额 ÷ 杠杆倍数”。
        """
        try:
            # 读取输入
            order_value = self.order_value_input.value()
            dca_count = self.dca_count_input.value() + 1
            dca_multiplier = self.dca_multiplier_input.value()
            leverage = self.leverage_input.value()

            # 计算每步累加投资
            step_list = []
            current_investment = order_value
            step_list.append(current_investment)

            for _ in range(1, dca_count):
                added_funds = current_investment * dca_multiplier
                current_investment += added_funds
                step_list.append(current_investment)

            # 最后一项为杠杆金额
            total_investment = step_list[-1] if step_list else 0
            # 实际金额 = 最后一步的累计投资 ÷ 杠杆倍数
            actual_investment = total_investment / leverage if leverage != 0 else 0

            # 顶部标签：显示“杠杆金额”与“实际金额”
            self.result_label.setText(
                f"杠杆金额: {total_investment:.2f}  |  实际金额: {actual_investment:.2f}"
            )

            # ========== 更新表格 ==========
            self.table.setRowCount(len(step_list))
            for idx, val in enumerate(step_list):
                # 步骤名称
                if idx == 0:
                    step_name = "初始金额"
                else:
                    step_name = f"DCA{idx}"

                # 第二列（“杠杆金额”列） => val
                # 第三列（“实际金额”列） => val / leverage
                real_val = val / leverage if leverage != 0 else 0

                # 设置单元格内容 & 居中
                step_item = QTableWidgetItem(step_name)
                step_item.setTextAlignment(Qt.AlignCenter)

                lever_item = QTableWidgetItem(f"{val:.2f}")
                lever_item.setTextAlignment(Qt.AlignCenter)

                actual_item = QTableWidgetItem(f"{real_val:.2f}")
                actual_item.setTextAlignment(Qt.AlignCenter)

                self.table.setItem(idx, 0, step_item)
                self.table.setItem(idx, 1, lever_item)
                self.table.setItem(idx, 2, actual_item)

        except ValueError:
            self.result_label.setText("输入有误，请检查数值！")

    def closeEvent(self, event):
        """
        窗口关闭事件：在关闭时自动保存窗口大小、位置以及当前输入值到 QSettings。
        """
        # 保存尺寸和位置
        self.settings.setValue('window_size', self.size())
        self.settings.setValue('window_position', self.pos())

        # 保存输入参数
        self.settings.setValue('order_value', self.order_value_input.value())
        self.settings.setValue('dca_count', self.dca_count_input.value())
        self.settings.setValue('dca_multiplier', self.dca_multiplier_input.value())
        self.settings.setValue('leverage', self.leverage_input.value())

        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = InvestmentCalculator()
    window.show()
    sys.exit(app.exec_())
