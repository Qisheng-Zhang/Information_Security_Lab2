"""Qt 主程序：交互与后台搜索，不访问 Tkinter 或其他桌面窗口。"""

import json
import os
from pathlib import Path
import queue
import secrets
import sys
import threading
import time

from PySide6.QtCore import QByteArray, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QTableWidgetItem

from .attacks import AttackCancelled, meet_in_the_middle
from .core import block_to_state, decrypt_block, decrypt_trace, encrypt_block, encrypt_trace
from .encoding import blocks_to_bytes, escape_bytes, format_bits, parse_number
from .modes import PROFILE, CipherPacket, cbc_decrypt, decrypt_packet, encrypt_ascii, generate_iv
from .multiple import double_decrypt, double_encrypt, triple_decrypt, triple_encrypt
from .qt_ui import WorkspaceUI, icon
from .version import __version__


class SaesWindow(WorkspaceUI, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"S-AES Studio {__version__} · 密码学实验室")
        self.setWindowIcon(icon("lock", "#7D6E98", 64))
        self.resize(1280,880)
        self.setMinimumSize(1060,720)
        self.last_block_output=None
        self.multi_output_value=None
        self.current_trace=None
        self.block_dirty=False
        self.attack_running=False
        self.attack_candidates=[]
        self.attack_cancel=threading.Event()
        self.attack_queue=queue.Queue()
        self.build_workspace()
        self.attack_timer=QTimer(self)
        self.attack_timer.setInterval(50)
        self.attack_timer.timeout.connect(self.poll_attack)
        self.copy_feedback_timer = QTimer(self)
        self.copy_feedback_timer.setSingleShot(True)
        self.copy_feedback_timer.timeout.connect(self.reset_copy_feedback)
        self.random_iv()
        self.generate_cross()
        self.load_attack_demo()
        self.run_block()
        self.block_input.textEdited.connect(self.mark_block_dirty)
        self.block_key.textEdited.connect(self.mark_block_dirty)
        self.ascii_plain.textChanged.connect(lambda:self.update_text_count(self.ascii_plain,self.ascii_count))
        self.cbc_plain.textChanged.connect(lambda:self.update_text_count(self.cbc_plain,self.cbc_count))
        self.update_text_count(self.ascii_plain,self.ascii_count)
        self.update_text_count(self.cbc_plain,self.cbc_count)
        self.shortcuts=[]
        for sequence,callback in (
            ("Alt+Left",lambda:self.move_trace(-1)),
            ("Alt+Right",lambda:self.move_trace(1)),
            ("Ctrl+Return",lambda:self.run_block(False)),
            ("Ctrl+Shift+Return",lambda:self.run_block(True)),
        ):
            shortcut=QShortcut(QKeySequence(sequence),self)
            shortcut.activated.connect(lambda operation=callback:self.guard(operation) if self.stack.currentIndex()==0 else None)
            self.shortcuts.append(shortcut)

    def show_status(self,text,error=False):
        self.status_label.setText(text)
        self.status_label.setProperty("error",error)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def guard(self,callback):
        try:
            callback()
        except (ValueError,OSError) as exc:
            self.show_status(f"请检查输入 · {exc}",True)

    def mark_block_dirty(self):
        self.block_dirty=True
        self.reset_copy_feedback()
        self.output_caption.setText("输入已更新 · 请重新运算")
        self.result_tag.setText("待更新")
        self.result_tag.setProperty("dirty",True)
        self.result_tag.style().unpolish(self.result_tag)
        self.result_tag.style().polish(self.result_tag)
        self.copy_button.setEnabled(False)
        self.fill_button.setEnabled(False)

    def parse_edit(self,edit,bits=16):
        try:
            value=parse_number(edit.text(),bits)
        except ValueError:
            edit.setProperty("invalid",True)
            edit.style().unpolish(edit)
            edit.style().polish(edit)
            if edit in (self.block_input,self.block_key): self.mark_block_dirty()
            raise
        edit.setProperty("invalid",False)
        edit.style().unpolish(edit)
        edit.style().polish(edit)
        return value

    def update_text_count(self,editor,counter):
        text=editor.toPlainText()
        try:
            length=len(text.encode("ascii"))
        except UnicodeEncodeError:
            counter.setText("含非 ASCII 字符 · 请输入英文、数字或符号")
            return
        counter.setText(f"{length} Bytes · {(length+1)//2} 组"+(" · 末组补 1 字节" if length%2 else ""))

    def run_block(self,decrypt=False):
        key=self.parse_edit(self.block_key)
        block=self.parse_edit(self.block_input)
        trace=(decrypt_trace if decrypt else encrypt_trace)(block,key)
        self.current_trace=trace
        self.reset_copy_feedback()
        self.last_block_output=trace.output
        self.output_hex.setText(f"{trace.output:04X}")
        self.result_card.set_value(trace.output)
        self.output_binary.setText(format_bits(trace.output))
        self.output_caption.setText("解密得到明文" if decrypt else "加密得到密文")
        self.block_dirty=False
        self.result_tag.setText("已解密 · 16 BIT" if decrypt else "已加密 · 16 BIT")
        self.result_tag.setProperty("dirty",False)
        self.result_tag.style().unpolish(self.result_tag)
        self.result_tag.style().polish(self.result_tag)
        self.copy_button.setEnabled(True)
        self.fill_button.setEnabled(True)
        for i,value in enumerate(trace.round_keys): self.key_labels[i].setText(f"K{i}  {value:04X}")
        self.trace_table.setRowCount(len(trace.steps))
        for index,step in enumerate(trace.steps):
            phase="输入" if index==0 else "初始轮" if index==1 else "第 1 轮" if index<=5 else "第 2 轮"
            transform_name = step.name.split("·", 1)[-1].strip()
            values=(phase,transform_name,f"{step.state:04X}",format_bits(step.state))
            for column,text in enumerate(values):
                item=QTableWidgetItem(text)
                if column>=2: item.setFont(QFont("Consolas",10))
                if index==len(trace.steps)-1:
                    item.setBackground(QColor("#F5EDF8")); item.setForeground(QColor("#876D96"))
                elif index%2: item.setBackground(QColor("#FFFCF9"))
                self.trace_table.setItem(index,column,item)
        self.trace_table.selectRow(len(trace.steps)-1)
        self.filter_trace()
        QTimer.singleShot(0,self.ensure_trace_visible)
        self.show_status(f"{'解密' if decrypt else '加密'}完成 · {block:04X} → {trace.output:04X}")

    def show_selected_state(self):
        index=self.trace_table.currentRow()
        if self.current_trace is None or not 0<=index<len(self.current_trace.steps): return
        step=self.current_trace.steps[index]
        previous=self.current_trace.steps[index-1].state if index else None
        self.state_matrix.set_value(step.state,previous)
        self.state_step.setText(f"{index+1:02} / {len(self.current_trace.steps):02}")
        self.state_hex.setText(f"{step.state:04X}")
        delta=f"Δ {(step.state^previous).bit_count()} / 16 bit 改变" if previous is not None else "输入状态 · 每格 4 bit"
        self.state_caption.setText(f"{step.name}\n{delta}")
        visible=self.visible_trace_rows()
        self.prev_step_button.setEnabled(bool(visible) and index!=visible[0])
        self.next_step_button.setEnabled(bool(visible) and index!=visible[-1])

    def visible_trace_rows(self):
        return [index for index in range(self.trace_table.rowCount()) if not self.trace_table.isRowHidden(index)]

    def ensure_trace_visible(self):
        current=self.trace_table.currentRow()
        if current>=0:
            self.trace_table.scrollToItem(self.trace_table.item(current,0))

    def filter_trace(self,_phase=None):
        if self.current_trace is None: return
        phase=self.phase_group.checkedId()
        for index in range(len(self.current_trace.steps)):
            stage=1 if index<=1 else 2 if index<=5 else 3
            self.trace_table.setRowHidden(index,phase!=0 and phase!=stage)
        visible=self.visible_trace_rows()
        if visible and self.trace_table.currentRow() not in visible:
            self.trace_table.selectRow(visible[0])
        self.show_selected_state()

    def move_trace(self,direction):
        if self.current_trace is None: return
        visible=self.visible_trace_rows()
        if not visible: return
        current=self.trace_table.currentRow()
        position=visible.index(current) if current in visible else 0
        position=max(0,min(len(visible)-1,position+direction))
        self.trace_table.selectRow(visible[position])
        self.trace_table.scrollToItem(self.trace_table.item(visible[position],0))
        self.show_selected_state()

    def fill_block(self):
        if self.last_block_output is None: raise ValueError("请先完成一次运算")
        if self.block_dirty: raise ValueError("输入已更新，请重新运算后再回填")
        self.block_input.setText(f"{self.last_block_output:04X}")
        self.mark_block_dirty()

    def copy_block(self):
        if self.last_block_output is None: raise ValueError("暂无可复制结果")
        if self.block_dirty: raise ValueError("输入已更新，请重新运算后再复制")
        QApplication.clipboard().setText(f"{self.last_block_output:04X}")
        self.copy_button.setText("已复制")
        self.copy_button.setIcon(icon("check", "#8EA67E", 16))
        self.copy_feedback_timer.start(1400)
        self.show_status("已复制完整 HEX 结果，包含前导零")

    def reset_copy_feedback(self):
        self.copy_feedback_timer.stop()
        self.copy_button.setText("复制")
        self.copy_button.setIcon(icon("copy", "#A38CB3", 16))

    def random_block(self):
        self.block_input.setText(f"{secrets.randbits(16):04X}")
        self.block_key.setText(f"{secrets.randbits(16):04X}")
        self.mark_block_dirty()

    def save_text(self,text,name):
        if not text.strip(): raise ValueError("暂无可保存内容")
        filename,_=QFileDialog.getSaveFileName(self,"保存文件",name,"JSON 文件 (*.json);;所有文件 (*)")
        if filename:
            Path(filename).write_text(text,encoding="utf-8")
            self.show_status(f"已保存 · {Path(filename).name}")

    def save_editor(self,editor,name): self.save_text(editor.toPlainText(),name)

    def load_editor(self,editor):
        filename,_=QFileDialog.getOpenFileName(self,"导入文件","","JSON 文件 (*.json);;所有文件 (*)")
        if filename:
            editor.setPlainText(Path(filename).read_text(encoding="utf-8-sig"))
            self.show_status(f"已导入 · {Path(filename).name}")

    def generate_cross(self):
        inputs=[(0x6F6B,0xA73B),(0,0),(65535,65535),(0x8000,1),(0x1234,0xABCD)]
        inputs.extend((secrets.randbits(16),secrets.randbits(16)) for _ in range(3))
        data={"profile":PROFILE,"vectors":[{"plaintext":f"{p:04X}","key":f"{k:04X}","ciphertext":f"{encrypt_block(p,k):04X}"} for p,k in inputs]}
        self.cross_text.setPlainText(json.dumps(data,indent=2))
        self.cross_summary.setText("8 组向量已生成 · 等待对方验证")
        self.cross_result.setPlainText("导出本组向量交给另一实现，或导入对方生成的文件。\n\n生成后验证自己的向量属于自检。")

    def verify_cross(self):
        try: data=json.loads(self.cross_text.toPlainText())
        except ValueError as exc: raise ValueError("测试向量不是有效 JSON") from exc
        if not isinstance(data,dict) or data.get("profile")!=PROFILE or not isinstance(data.get("vectors"),list):
            raise ValueError("测试向量 profile 或 vectors 格式错误")
        if not data["vectors"]: raise ValueError("测试向量不能为空")
        lines=[]; passed=0
        for index,entry in enumerate(data["vectors"],1):
            fields=("plaintext","key","ciphertext")
            if not isinstance(entry,dict) or not all(isinstance(entry.get(f),str) and len(entry[f])==4 and all(c in "0123456789abcdefABCDEF" for c in entry[f]) for f in fields):
                raise ValueError(f"第 {index} 行 P / K / C 必须为 4 位 HEX")
            p,k,c=(int(entry[field],16) for field in fields)
            actual,recovered=encrypt_block(p,k),decrypt_block(c,k)
            ok=actual==c and recovered==p; passed+=ok
            lines.append(f"{'通过' if ok else '失败'}  {index:02}  P={p:04X}  K={k:04X}\n      对方C={c:04X}  本组C={actual:04X}  解密={recovered:04X}")
        self.cross_summary.setText(f"{passed} / {len(lines)} 组通过 · {'结果一致' if passed==len(lines) else '存在差异'}")
        self.cross_result.setPlainText("\n\n".join(lines))
        self.show_status(f"交叉验证完成 · {passed}/{len(lines)} 组通过")

    def encrypt_ascii_gui(self):
        packet=encrypt_ascii(self.ascii_plain.toPlainText(),self.parse_edit(self.ascii_key))
        self.ascii_packet.setPlainText(packet.to_json())
        raw=escape_bytes(blocks_to_bytes(list(packet.blocks)))
        self.ascii_preview.setText("密文 RAW  "+(raw[:240]+"…" if len(raw)>240 else raw))
        self.show_status(f"ASCII 加密完成 · {packet.original_length} 字节 / {len(packet.blocks)} 个分组")

    def decrypt_ascii_gui(self):
        packet=CipherPacket.from_json(self.ascii_packet.toPlainText())
        if packet.mode!="ECB": raise ValueError("请在 CBC 页解密 CBC 密文包")
        data=decrypt_packet(packet,self.parse_edit(self.ascii_key))
        try: text=data.decode("ascii")
        except UnicodeDecodeError as exc: raise ValueError("解密后含非 ASCII 字节，请检查密钥或密文") from exc
        self.ascii_plain.setPlainText(text)
        self.ascii_preview.setText("已还原 · "+escape_bytes(data))
        self.show_status("ASCII 解密完成 · 原始长度与换行已保留")

    def multi_mode_changed(self):
        if not hasattr(self,"multi_key"): return
        self.multi_key.setText("1F2E3D4C5A6B" if self.multi_mode.currentIndex()==1 else "1F2E3D4C")

    def run_multiple(self,decrypt=False):
        mode=self.multi_mode.currentIndex(); bits=48 if mode==1 else 32
        key=self.parse_edit(self.multi_key,bits); block=self.parse_edit(self.multi_input)
        if mode==0: value=(double_decrypt if decrypt else double_encrypt)(block,key)
        else: value=(triple_decrypt if decrypt else triple_encrypt)(block,key,bits)
        self.multi_output_value=value
        self.multi_output.setText(f"{'明文 P' if decrypt else '密文 C'}   {value:04X}\n\n{format_bits(value)}")
        self.show_status(self.multi_mode.currentText()+" · 运算完成")

    def fill_multiple(self):
        if self.multi_output_value is None: raise ValueError("请先完成一次多重运算")
        self.multi_input.setText(f"{self.multi_output_value:04X}")

    def load_attack_demo(self):
        self.attack_pairs.setPlainText("\n".join(f"{p:04X} {double_encrypt(p,0x1F2E3D4C):04X}" for p in (0x6F6B,0x1234,0xBEEF)))

    def start_attack(self):
        if self.attack_running: return
        pairs=[]
        for index,line in enumerate(self.attack_pairs.toPlainText().splitlines(),1):
            if not line.strip(): continue
            parts=line.replace(","," ").split()
            if len(parts)!=2 or not all(len(p)==4 and all(c in "0123456789abcdefABCDEF" for c in p) for p in parts):
                raise ValueError(f"第 {index} 行应是两个 4 位 HEX：P C")
            pairs.append(tuple(int(p,16) for p in parts))
        if not pairs: raise ValueError("至少需要一组已知明密文对")
        self.attack_cancel.clear(); self.attack_candidates=[]; self.attack_running=True
        self.attack_start_button.setEnabled(False); self.attack_cancel_button.setEnabled(True)
        self.attack_progress.setValue(0)
        self.attack_result.setPlainText("正在完整搜索 K1 / K2 …\n\n可以切换页面，或取消本次搜索。")
        started=time.perf_counter()
        def worker():
            try:
                def progress(stage,done,total):
                    self.attack_queue.put(("progress",(stage,done+(0 if stage.startswith("建立") else total))))
                keys=meet_in_the_middle(pairs,progress,self.attack_cancel)
                self.attack_queue.put(("done",(keys,time.perf_counter()-started)))
            except AttackCancelled: self.attack_queue.put(("cancel",None))
            except Exception as exc: self.attack_queue.put(("error",str(exc)))
        threading.Thread(target=worker,daemon=True).start()
        self.attack_timer.start()

    def poll_attack(self):
        try:
            while True:
                kind,data=self.attack_queue.get_nowait()
                if kind=="progress":
                    stage,value=data; self.attack_progress.setValue(value)
                    self.attack_status.setText(f"{stage}  ·  {value/131072:.0%}")
                    continue
                self.attack_running=False
                self.attack_start_button.setEnabled(True); self.attack_cancel_button.setEnabled(False)
                if kind=="done":
                    keys,elapsed=data; self.attack_candidates=keys
                    lines=[f"{key:08X}    K1={key>>16:04X}   K2={key&65535:04X}" for key in keys[:100]]
                    note="唯一候选符合全部已知对。" if len(keys)==1 else "请增加不同明文的已知对继续筛选。" if keys else "没有密钥符合全部已知对。"
                    self.attack_result.setPlainText(f"{len(keys)} 个候选  /  {elapsed:.2f} 秒\n\n"+"\n".join(lines)+f"\n\n{note}"+("\n仅展示前 100 个，可导出全部。" if len(keys)>100 else ""))
                    self.attack_status.setText(f"搜索完成 · {len(keys)} 个候选")
                    self.show_status("中间相遇搜索完成")
                else:
                    self.attack_result.setPlainText("搜索已取消" if kind=="cancel" else f"搜索失败：{data}")
                    self.attack_status.setText("已取消" if kind=="cancel" else "搜索失败")
                self.attack_timer.stop()
        except queue.Empty: pass

    def save_candidates(self):
        if not self.attack_candidates: raise ValueError("暂无候选，请先完成搜索")
        self.save_text(json.dumps([f"{key:08X}" for key in self.attack_candidates],indent=2),"candidate_keys.json")

    def random_iv(self): self.cbc_iv.setText(f"{generate_iv():04X}")

    def encrypt_cbc_gui(self):
        packet=encrypt_ascii(self.cbc_plain.toPlainText(),self.parse_edit(self.cbc_key),"CBC",self.parse_edit(self.cbc_iv))
        self.cbc_packet.setPlainText(packet.to_json())
        self.cbc_comparison.setPlainText(f"{packet.original_length} 字节 / {len(packet.blocks)} 组已加密。\nIV={packet.iv:04X} 已写入密文包，可与接收方共享。")
        self.show_status("CBC 加密完成")

    def read_cbc(self):
        packet=CipherPacket.from_json(self.cbc_packet.toPlainText())
        if packet.mode!="CBC": raise ValueError("此页只接受 CBC 密文包")
        return packet,self.parse_edit(self.cbc_key)

    def decrypt_cbc_gui(self):
        packet,key=self.read_cbc()
        data=decrypt_packet(packet,key)
        try: text=data.decode("ascii")
        except UnicodeDecodeError as exc: raise ValueError("解密后含非 ASCII 字节，请检查密钥；篡改实验请使用对比解密") from exc
        self.cbc_plain.setPlainText(text); self.cbc_iv.setText(f"{packet.iv:04X}")
        self.show_status("CBC 解密完成 · 使用包内 IV")

    def compare_tamper(self):
        packet,key=self.read_cbc()
        if not packet.blocks: raise ValueError("空消息没有可篡改分组，请先加密非空消息")
        try: index=int(self.tamper_index.text())-1
        except ValueError as exc: raise ValueError("分组编号必须为整数") from exc
        if not 0<=index<len(packet.blocks): raise ValueError(f"分组编号应为 1 到 {len(packet.blocks)}")
        value=self.parse_edit(self.tamper_value)
        changed=list(packet.blocks)
        changed[index]=changed[index]^value if self.tamper_mode.currentIndex()==0 else value
        before=cbc_decrypt(list(packet.blocks),key,packet.iv); after=cbc_decrypt(changed,key,packet.iv)
        lines=[f"C{index+1}: {packet.blocks[index]:04X} → {changed[index]:04X}   Δ={packet.blocks[index]^changed[index]:04X}","","分组   原明文   修改后   XOR 差值"]
        lines.extend(f"P{i:<4}  {a:04X}     {b:04X}     {a^b:04X}" for i,(a,b) in enumerate(zip(before,after),1))
        lines.extend(("","篡改前："+escape_bytes(blocks_to_bytes(before,packet.original_length)),"篡改后："+escape_bytes(blocks_to_bytes(after,packet.original_length))))
        self.cbc_comparison.setPlainText("\n".join(lines))
        self.show_status("篡改对比完成 · 原密文包保持不变")

    def closeEvent(self,event):
        self.attack_cancel.set(); self.attack_timer.stop(); super().closeEvent(event)


def create_application():
    application=QApplication.instance()
    if application is None:
        application=QApplication(sys.argv)
        application.setStyle("Fusion")
        # 某些受限的离屏环境不枚举系统字体；从本机读取，不分发字体文件。
        if sys.platform=="win32" and not QFontDatabase.families():
            fonts=Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts"
            for filename in ("msyh.ttc","msyhbd.ttc","segoeui.ttf","consola.ttf"):
                try: QFontDatabase.addApplicationFontFromData(QByteArray((fonts/filename).read_bytes()))
                except OSError: pass
        application.setFont(QFont("Microsoft YaHei UI",10))
        application.setApplicationName("S-AES Studio")
    return application


def main():
    application=create_application()
    window=SaesWindow(); window.show()
    return application.exec()
