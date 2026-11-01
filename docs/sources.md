# 設計根拠・依存物

参照日: 2026-11-01。データシートの典型値は部品の評価条件での値で、本基板の性能保証ではありません。

## 一次資料

- ST STM32H743VI: https://www.st.com/resource/en/datasheet/stm32h743vi.pdf
- ST STM32H7 reference manual RM0433: https://www.st.com/resource/en/reference_manual/rm0433-stm32h742-stm32h743753-and-stm32h750-value-line-advanced-armbased-32bit-mcus-stmicroelectronics.pdf
- TI PCM3060: https://www.ti.com/lit/ds/symlink/pcm3060.pdf — ピン、ハードウェア制御、入出力振幅、I²S、ADC/DAC群遅延
- TI TLV9062: https://www.ti.com/lit/ds/symlink/tlv9062.pdf
- TI TPS22918: https://www.ti.com/lit/ds/symlink/tps22918.pdf — 6端子ピン割当、CTとスルーレート
- ST LD1117: https://www.st.com/resource/en/datasheet/ld1117.pdf
- JLCPCB STM32H743VIT6 C114409: https://jlcpcb.com/partdetail/C114409
- JLCPCB USBLC6-2SC6 C7519: https://jlcpcb.com/partdetail/C7519
- JLCPCB USB-C C165948: https://jlcpcb.com/partdetail/C165948
- LCSC PCM3060PWR C2651841: https://www.lcsc.com/product-detail/C2651841.html
- JLCPCB Basic例、10 kΩ C25804: https://jlcpcb.com/partdetail/C25804
- JLCPCB Basic例、100 nF C14663: https://jlcpcb.com/partdetail/C14663

全抵抗の候補番号と個別参照URLは `downloads/bom_master.csv` にあります。調達区分を確認できなかった品目は推測でBasicにしていません。

## 固定したファームウェア依存物

|ライブラリ|バージョン / コミット|ライセンス|
|---|---|---|
|ST STM32H7 HAL|v1.11.3 / fec141ce999da655a48e1a15db83a72d564a1312|BSD-3-Clause|
|ST CMSIS Device H7|v1.10.5 / e4d57d6edc39f35aced298732829fc2a5e6a8a71|Apache-2.0|
|Arm CMSIS 5|5.9.0 / 2b7495b8535bdcb306dac29b9ded4cfb679d7e5c|Apache-2.0ほかファイル記載|
|TinyUSB|0.18.0 / 86ad6e56c1700e85f1c5678607a762cfe3aa2f47|MIT|

取得先は `tools/bootstrap.sh`、再配布ライセンス文は `LICENSES/` に含みます。依存ソース自体はZIPへ重複同梱せず、固定コミットから取得します。OLEDグリフとDSPコードはこのプロジェクトで作成しました。

配布バイナリにはnewlibのC/数学ライブラリとGCCランタイムがリンクされています。newlibの各著作権表示およびGCC Runtime Library Exception関連文も `LICENSES/` に収録しています。

## CAD・ツール

KiCad 9.0.2の標準シンボルとフットプリントから必要なものを `hardware/symbols`、`hardware/VoicePitcher.pretty` に同梱しています。KiCad LibrariesはCC-BY-SA 4.0 + KiCad Libraries Exceptionです。出典: https://www.kicad.org/libraries/license/ 、https://gitlab.com/kicad/libraries 。派生ライブラリにも同じ条件が適用されます。

改変点は、継承シンボルの解決、CUIジャックのパッド名を物理番号1/2/3からS/T/Rへ対応、PCM3060 DEMPの端子種別をハードウェアモードの入力へ変更です。TPS22918のシンボルはTIデータシートに基づき作成しました。ライブラリ例外により、これらを使った基板自体へCC-BY-SAを強制するものではありません。

配線はFreerouting 1.9.0（GPL-3.0）を使用。ツール本体は配布ZIPへ含めません。入出力DSN/SESはビルド中間データです。公式: https://github.com/freerouting/freerouting 。ホストDSP検証はGCC、numpy、AddressSanitizer/UndefinedBehaviorSanitizer、PDF作成はReportLabとInkscapeです。
