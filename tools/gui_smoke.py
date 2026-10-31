"""Qt GUI 集成检查；--offscreen 不显示桌面窗口，--render 只生成临时布局检查图。"""

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
QA_TEMP=ROOT/"build/gui-qa"


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offscreen",action="store_true")
    parser.add_argument("--render",action="store_true")
    parser.add_argument("--keep-open",action="store_true")
    args=parser.parse_args()
    if args.offscreen: os.environ["QT_QPA_PLATFORM"]="offscreen"

    from PySide6 import __version__ as qt_version
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QFileDialog,QPushButton
    from saes.core import encrypt_block
    from saes.modes import CipherPacket
    from saes.qt_gui import SaesWindow,create_application
    from saes.version import __version__ as app_version

    app=create_application()
    window=SaesWindow(); window.show(); app.processEvents()
    cases=[]
    def check(name,condition):
        if not condition: raise AssertionError(name)
        cases.append({"case":name,"passed":True})
    def search_wait(timeout=30):
        deadline=time.monotonic()+timeout
        while window.attack_running and time.monotonic()<deadline:
            app.processEvents(); time.sleep(0.005)
        if window.attack_running: raise AssertionError("搜索超时")

    try:
        QTest.mouseClick(window.encrypt_button,Qt.MouseButton.LeftButton)
        check("真实按钮点击显示 0738 与九个轮状态",window.output_hex.text()=="0738" and window.trace_table.rowCount()==9)
        window.fill_block(); QTest.mouseClick(window.decrypt_button,Qt.MouseButton.LeftButton)
        check("回填并点击解密还原 6F6B",window.last_block_output==0x6F6B)
        window.block_input.setText("6F6B"); window.run_block()
        window.copy_button.click()
        check("复制成功反馈显示在按钮上",window.copy_button.text()=="已复制")
        check("复制结果保留前导零",app.clipboard().text()=="0738")
        window.block_input.setText("1234"); window.mark_block_dirty()
        check("输入更新后撤销旧复制反馈",window.copy_button.text()=="复制" and not window.copy_button.isEnabled())
        window.block_input.setText("6F6B"); window.run_block()
        window.trace_table.selectRow(0); app.processEvents()
        check("选择轮状态同步四格矩阵",window.state_matrix.value==0x6F6B)
        window.phase_buttons[2].click(); app.processEvents()
        check("第1轮筛选只保留四次变换",window.visible_trace_rows()==[2,3,4,5] and window.trace_table.currentRow()==2)
        window.prev_step_button.click()
        check("逐步查看不越过当前轮边界",window.trace_table.currentRow()==2 and not window.prev_step_button.isEnabled())
        window.next_step_button.click(); app.processEvents()
        check("行移位仅高亮第二行两个单元格",window.trace_table.currentRow()==3 and window.state_matrix.changed_cells==(2,3))
        window.phase_buttons[0].click(); window.trace_table.selectRow(0); app.processEvents()
        window.block_input.setFocus(); QTest.keyClick(window.block_input,Qt.Key.Key_A,Qt.KeyboardModifier.ControlModifier); QTest.keyClicks(window.block_input,"1234")
        check("编辑输入提示结果尚未更新","请重新运算" in window.output_caption.text())
        check("输入更新后禁用旧密文复制与回填",not window.copy_button.isEnabled() and not window.fill_button.isEnabled())
        QTest.keyClick(window.block_input,Qt.Key.Key_Return,Qt.KeyboardModifier.ControlModifier); app.processEvents()
        check("Ctrl+Enter 使用当前输入加密并恢复结果操作",window.last_block_output==encrypt_block(0x1234,0xA73B) and window.copy_button.isEnabled() and window.fill_button.isEnabled())
        window.block_input.setText("ZZZZ"); QTest.mouseClick(window.encrypt_button,Qt.MouseButton.LeftButton)
        check("非法输入以状态提示且不阻塞","请检查输入" in window.status_label.text())
        check("非法分组字段得到错误标记",window.block_input.property("invalid") is True)
        window.block_input.setText("6F6B"); window.run_block()
        check("修正输入后清除错误并同步四组二进制",window.block_input.property("invalid") is False and ''.join(part.text() for part in window.output_binary.groups)==f'{window.last_block_output:016b}')

        window.nav_buttons[1].click(); app.processEvents()
        check("侧边导航切换页面与标题",window.stack.currentIndex()==1 and window.title_label.text()=="交叉测试")
        window.verify_cross()
        check("交叉向量自检全部通过","8 / 8" in window.cross_summary.text())
        data=json.loads(window.cross_text.toPlainText()); data["vectors"][0]["ciphertext"]="FFFF"
        window.cross_text.setPlainText(json.dumps(data)); window.verify_cross()
        check("交叉验证能识别错误密文","失败  01" in window.cross_result.toPlainText())
        data["vectors"]=[{"plaintext":"0b01","key":"0B10","ciphertext":f"{encrypt_block(0x0B01,0x0B10):04X}"}]
        window.cross_text.setPlainText(json.dumps(data)); window.verify_cross()
        check("JSON 内 0B 开头 HEX 无歧义","1 / 1" in window.cross_summary.text())

        window.select_page(2); window.ascii_plain.setPlainText("ABC")
        check("ASCII 奇数长度显示实际补齐提示","3 Bytes" in window.ascii_count.text() and "补 1 字节" in window.ascii_count.text())
        window.ascii_plain.setPlainText("ABC\n"); window.encrypt_ascii_gui()
        check("换行计入ASCII字节数且偶数长度不补齐","4 Bytes" in window.ascii_count.text() and "补" not in window.ascii_count.text())
        packet=window.ascii_packet.toPlainText()
        check("ASCII 密文预览未误显示明文",window.ascii_preview.text().startswith("密文 RAW") and "ABC\n" not in window.ascii_preview.text())
        QA_TEMP.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=QA_TEMP) as folder:
            saved=Path(folder)/"cipher.json"
            with patch.object(QFileDialog,"getSaveFileName",return_value=(str(saved),"JSON")):
                window.save_editor(window.ascii_packet,"ascii_cipher.json")
            check("密文包真实导出成功",saved.read_text(encoding="utf-8")==packet)
            fresh=SaesWindow()
            with patch.object(QFileDialog,"getOpenFileName",return_value=(str(saved),"JSON")):
                fresh.load_editor(fresh.ascii_packet)
            fresh.decrypt_ascii_gui()
            check("另一新窗口直接导入解密且保留尾换行",fresh.ascii_plain.toPlainText()=="ABC\n")
            fresh.close()
        window.ascii_plain.setPlainText(""); window.ascii_packet.setPlainText(packet); window.decrypt_ascii_gui()
        check("ASCII 空工作区导入后能还原",window.ascii_plain.toPlainText()=="ABC\n")

        window.select_page(3)
        for mode in range(3):
            window.multi_mode.setCurrentIndex(mode); window.multi_input.setText("6F6B"); window.run_multiple()
            window.fill_multiple(); window.run_multiple(True)
            check(f"多重模式 {mode+1} 往返",window.multi_output_value==0x6F6B)
        window.multi_mode.setCurrentIndex(1); window.multi_key.setText("00001F2E3D4C"); window.multi_input.setText("1234")
        window.run_multiple(); window.fill_multiple(); window.run_multiple(True)
        check("48 bit 前导零密钥未切换为 32 bit",window.multi_output_value==0x1234)
        window.start_attack(); search_wait()
        check("Qt 后台搜索唯一恢复组合密钥",window.attack_candidates==[0x1F2E3D4C])
        success_text=window.attack_result.toPlainText()
        window.start_attack(); window.attack_cancel.set(); search_wait()
        check("取消搜索后按钮恢复",window.attack_start_button.isEnabled() and not window.attack_cancel_button.isEnabled() and "已取消" in window.attack_result.toPlainText())

        window.select_page(4); window.cbc_iv.setText("1357"); window.encrypt_cbc_gui()
        check("CBC计数与密文包原始长度一致",f'{CipherPacket.from_json(window.cbc_packet.toPlainText()).original_length} Bytes' in window.cbc_count.text())
        cbc_packet=CipherPacket.from_json(window.cbc_packet.toPlainText())
        window.cbc_iv.setText("FFFF"); window.decrypt_cbc_gui()
        check("CBC 使用包内共享 IV 解密",window.cbc_iv.text()=="1357" and window.cbc_plain.toPlainText()=="Hello, S-AES CBC mode!")
        window.compare_tamper()
        check("CBC 翻转对比含逐组 XOR 差值","P2" in window.cbc_comparison.toPlainText() and "0001" in window.cbc_comparison.toPlainText())
        window.tamper_mode.setCurrentIndex(1); window.tamper_value.setText("0000"); window.compare_tamper()
        check("替换实验不修改原密文包",CipherPacket.from_json(window.cbc_packet.toPlainText())==cbc_packet)
        window.cbc_plain.setPlainText(""); window.encrypt_cbc_gui()
        try: window.compare_tamper()
        except ValueError: check("空消息篡改被清晰拒绝",True)
        else: check("空消息篡改应被拒绝",False)

        window.resize(1060,720)
        for index in range(5):
            window.select_page(index); app.processEvents()
            scroll=window.stack.widget(index)
            check(f"第 {index+1} 页小窗口可滚动访问且无横向溢出",scroll.horizontalScrollBar().maximum()==0)
        window.resize(1240,850)
        window.generate_cross(); window.verify_cross()
        window.ascii_plain.setPlainText("Hello, S-AES!"); window.encrypt_ascii_gui()
        window.multi_mode.setCurrentIndex(0); window.multi_input.setText("6F6B"); window.run_multiple()
        window.attack_candidates=[0x1F2E3D4C]; window.attack_result.setPlainText(success_text); window.attack_progress.setValue(131072); window.attack_status.setText("搜索完成 · 1 个候选")
        window.cbc_plain.setPlainText("Hello, S-AES CBC mode!"); window.cbc_iv.setText("1357"); window.encrypt_cbc_gui()
        window.tamper_mode.setCurrentIndex(0); window.tamper_value.setText("0001"); window.compare_tamper()
        if args.render:
            output=QA_TEMP/"render"; output.mkdir(parents=True,exist_ok=True)
            for index in range(5):
                window.select_page(index); app.processEvents(); window.grab().save(str(output/f"page-{index+1}.png"))
        window.select_page(0); window.block_input.setText("6F6B"); window.run_block(); app.processEvents()
        output=ROOT/"docs/results/gui_smoke.json"; output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps({"framework":"PySide6 / Qt Widgets","version":qt_version,"app_version":app_version,"offscreen":args.offscreen,"passed":len(cases),"cases":cases},ensure_ascii=False,indent=2),encoding="utf-8")
        print(f"Qt GUI 集成检查：{len(cases)} 项全部通过。",flush=True)
        if args.keep_open: return app.exec()
        return 0
    finally:
        window.close(); app.processEvents()


if __name__=="__main__":
    raise SystemExit(main())
