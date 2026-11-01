# Voice Pitcher — standalone audio DSP prototype

**98 × 98 mm、表面のみの部品実装、SSD1306表示器と4つの操作ボタンを備えた音声エフェクターの設計・ファームウェアです。** STM32H743とPCM3060を使い、ステレオライン入出力とUSB-Cオーディオを切り替えます。

現在は **Rev 0.1の未実機検証プロトタイプ** です。回路図ERC・基板DRC・未接続はすべて0件、回路図とPCBの端子接続も照合済みです。実機の起動、USB互換性、音質、遅延、消費電流、温度は未測定です。添付データは試作レビュー用で、量産承認済みではありません。

## ダウンロード

- [全データ ZIP](downloads/voice_pitcher_rev0.1_prototype.zip?raw=true) — 回路図、PCB、製造データ、ファームウェア、説明書、検証記録
- [ガーバー・ドリル ZIP](downloads/voice_pitcher_gerbers.zip?raw=true)
- [JLCPCB用 BOM](downloads/jlc_bom.csv?raw=true) / [CPL](downloads/jlc_cpl.csv?raw=true) / [調達状況付き全BOM](downloads/bom_master.csv?raw=true)
- [日本語説明書 PDF](downloads/voice_pitcher_manual_ja.pdf?raw=true) / [回路図 PDF](downloads/schematic.pdf?raw=true) / [表面実装図 PDF](downloads/assembly-top.pdf?raw=true)
- [ファームウェア BIN](downloads/firmware/voice_pitcher.bin?raw=true) / [HEX](downloads/firmware/voice_pitcher.hex?raw=true) / [ELF](downloads/firmware/voice_pitcher.elf?raw=true)
- [検証結果](downloads/reports/hardware.json) / [DSP周波数テスト](downloads/reports/dsp-spectral.json) / [SHA-256](downloads/SHA256SUMS.txt)
- [スクリーンショット全18枚 ZIP](downloads/voice_pitcher_screenshots.zip?raw=true) / [画像付きプレリリース](https://github.com/Xenoah/pcb_voice-pitcher/releases/tag/v0.1.0-prototype)

CSVはページ右上のDownload raw file、ZIPは上記リンクから保存できます。BOMの空欄LCSC番号は未確定部品です。注文前に [製造手順](docs/manufacturing.md) の照合が必要です。

## スクリーンショット

実際のKiCadデータとPDFから出力した設計画面です。実機写真ではありません。3Dモデル未提供のJ1（USB-C）、J2/J3（音声ジャック）、Y1（発振器）、および外付けOLEDは3D表示に含まれません。

**3D斜視** — 98 × 98 mm、全ての部品を表面に実装する設計。

![基板の3D斜視。CADレンダリング、未実機検証](downloads/screenshots/01-pcb-3d-angle.png)

**表裏・4層の一覧** — 上段は3D表裏、中段は表裏配線、下段はGND / 3.3 V内層。裏面図は裏側から見た向きです。

![基板の表裏、配線、GNDと3.3V内層の一覧](downloads/screenshots/00-board-overview.png)

**回路図全7ページと説明書** — 全体構成、MCU、電源、USB、コーデック、アナログ、表示・操作回路。

![回路図全7ページと日本語説明書の一覧](downloads/screenshots/00-schematic-overview.png)

<details>
<summary>個別の高解像度画像を表示</summary>

|3D表面|3D裏面|
|---|---|
|[![3D表面](downloads/screenshots/02-pcb-3d-top.png)](downloads/screenshots/02-pcb-3d-top.png)|[![3D裏面](downloads/screenshots/03-pcb-3d-bottom.png)](downloads/screenshots/03-pcb-3d-bottom.png)|
|表面配線|裏面配線|
|[![表面配線](downloads/screenshots/04-pcb-top-routing.png)](downloads/screenshots/04-pcb-top-routing.png)|[![裏面配線](downloads/screenshots/05-pcb-bottom-routing.png)](downloads/screenshots/05-pcb-bottom-routing.png)|
|L2 GND|L3 3.3 V|
|[![GND内層](downloads/screenshots/06-pcb-inner-ground.png)](downloads/screenshots/06-pcb-inner-ground.png)|[![3.3V内層](downloads/screenshots/07-pcb-inner-3v3.png)](downloads/screenshots/07-pcb-inner-3v3.png)|
|実装図|回路図：全体|
|[![実装図](downloads/screenshots/08-assembly-top.png)](downloads/screenshots/08-assembly-top.png)|[![全体構成](downloads/screenshots/09-schematic-overview.png)](downloads/screenshots/09-schematic-overview.png)|
|回路図：MCU|回路図：電源|
|[![MCU](downloads/screenshots/10-schematic-mcu.png)](downloads/screenshots/10-schematic-mcu.png)|[![電源](downloads/screenshots/11-schematic-power.png)](downloads/screenshots/11-schematic-power.png)|
|回路図：USB-C|回路図：コーデック|
|[![USB-C](downloads/screenshots/12-schematic-usb.png)](downloads/screenshots/12-schematic-usb.png)|[![コーデック](downloads/screenshots/13-schematic-codec.png)](downloads/screenshots/13-schematic-codec.png)|
|回路図：アナログ|回路図：OLED・スイッチ|
|[![アナログ](downloads/screenshots/14-schematic-analog.png)](downloads/screenshots/14-schematic-analog.png)|[![OLED・スイッチ](downloads/screenshots/15-schematic-ui.png)](downloads/screenshots/15-schematic-ui.png)|
|日本語説明書・先頭ページ|画像の生成元|
|[![日本語説明書](downloads/screenshots/16-manual.png)](downloads/screenshots/16-manual.png)|[CADハッシュ・3Dモデル出典・画像一覧](downloads/screenshots/manifest.json)|

</details>

画像を再生成する場合は `python3 tools/render_gallery.py --fetch-models` を実行します。KiCad 9、Inkscape、poppler-utils、Python Pillow/reportlabが必要です。

## 設計内容

|項目|Rev 0.1の内容|
|---|---|
|基板|98 × 98 mm、4層、部品は全てTOP。片面実装であり、片面銅箔基板ではありません|
|処理|STM32H743VIT6、400 MHz、32 bit float DSP、24 bit / 48 kHzステレオ|
|変換|PCM3060PWR、独立したADC/DAC、アナログ5 V・デジタル3.3 V|
|アナログ端子|入力・出力各1個の3.5 mm TRSステレオライン。6.35 mmは外付け変換アダプタ|
|USB-C|USB 2.0 Full Speed、UAC2のデバイス。PC・スマホ側がホスト|
|ルーティング|LINE→LINE、LINE→USB、USB→LINE、USB→USB|
|操作|SSD1306 128×64 I²C、MODE / DOWN / UP / I/O、別途RESET / BOOT|
|エフェクト|DRY、±12半音ピッチ変更、単音ピッチ補正、500 msディレイ、5 Hzトレモロ|
|スタンドアローン|PC不要のLINE→LINE動作。5 Vで1.5 A以上を広告するType-C電源を想定|
|調達|抵抗と100 nFを中心にJLCPCB Basicへ寄せた構成。全品Basicではありません|

**ピッチ変更を「音質ロスゼロ・遅延ゼロ」で行うことはできません。** 音程推定には観測時間が必要で、ADC/DAC・バッファにも遅延があります。本設計は専用基板上のMCUでリアルタイム処理します。無加工デジタルDRYは24 bit整数の往復一致をテスト済みですが、アナログ往復やピッチ処理の無損失を意味しません。

DRYのアナログ往復は計算上約2.1 msを起点とする設計です。ピッチ処理は可変遅延約1.3–65.3 ms、音程検出は約42.7 msの窓に分割演算と追従時間が加わります。USB経路はさらにホストのバッファに依存します。いずれも実測保証値ではありません。

## 使い方と設計資料

1. [ハードウェア仕様・ピン配置](docs/hardware.md)
2. [ファームウェア・操作・ビルド](docs/firmware.md)
3. [JLCPCB製造・部品調達](docs/manufacturing.md)
4. [検証済み範囲と実機チェック](docs/validation.md)
5. [データシートと依存ライブラリ](docs/sources.md)

通常のマイク、パッシブギター、ヘッドホンを直接つなぐための回路ではありません。マイクには外部プリアンプ、楽器には適切なバッファ、ヘッドホンには外部アンプを使用してください。USBホスト機能はないため、別のUSBオーディオインターフェースを本機へ直接接続する構成には対応しません。

KiCad 9で [hardware/voice_pitcher.kicad_pro](hardware/voice_pitcher.kicad_pro) を開けます。配線済みPCBは `voice_pitcher.kicad_pcb` です。`placement.kicad_pcb` は再配置・再配線用の中間ファイルです。

```sh
bash tools/bootstrap.sh
make test
make firmware
make hardware-check
make exports
python3 tools/package_release.py
```

必要なツールとインストール方法は [ビルド手順](docs/firmware.md) を参照してください。オリジナルコード・設計はMIT、同梱KiCadライブラリと外部依存物にはそれぞれのライセンスが適用されます。
