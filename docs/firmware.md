# ファームウェアと操作

## 実装した機能

起動時はDRY、LINE→LINEです。表示器が応答しなくても音声処理を継続します。設定はRAM上のみで、電源を切ると初期値へ戻ります。

|操作|動作|
|---|---|
|MODE短押し|DRY → PITCH SHIFT → AUTO TUNE → DELAY → TREMOLO|
|MODE 600 ms以上|補正スケールをChromatic → Major → Natural Minorへ切替|
|DOWN / UP、SHIFT時|−12～+12半音、1半音刻み|
|DOWN / UP、TUNE時|キーの根音C～Bを変更|
|DOWN / UP、DELAY時|フィードバックを0.05刻み、0～0.85へ変更|
|DOWN / UP、TREMOLO時|Wetを0.1刻み、0～1へ変更|
|I/O|LINE/LINE → LINE/USB → USB/LINE → USB/USB|
|RESET|MCUを再起動|
|BOOTを押しながらRESET|STM32 ROM bootloader用。Rev 0.1での書き込みはSWDを推奨|

OLEDにはモード、シフト量、検出Hz、MIDIノートとセント、入出力、キー/スケール、電源待ち・クリップ・アンダーランを表示します。クリップ/アンダーラン表示は再起動まで保持します。各モードのWetは共通パラメータで、TREMOLOで変更したWetは他のエフェクトにも適用されます。DRYには影響しません。

ピッチ推定は左チャンネルで行い、補正量を左右に同じように適用します。左右逆相で検出信号が消えないための仕様です。TUNE入力は単音の声・楽器、約70～800 Hzを想定し、和音・複数歌唱・強い雑音には適しません。検出信頼度が低いときは補正量を0へ戻します。

## DSP方式と制約

- 48 kHz、ステレオ32 bit float、32フレーム単位。
- SHIFTは2つの読み出しヘッドとsin²クロスフェードによる可変ディレイ。推定周期の偶数倍へグレイン長を追従させます。
- TUNEは12 kHzへ間引いた信号のYIN、512サンプルの窓、しきい値0.15、信頼度0.85以上。スケール内最近傍へ最大±2半音補正、追従時定数は初期値30 ms。
- 172ラグの推定演算を音声ブロックごとに分割し、1回に集中してDMA期限を超えない構造。
- ピッチ上げ時に4段ローパスを使い、エイリアスを減らします。上帯域を削るため無損失ではありません。
- DELAYは500 ms、固定Wet混合35%、フィードバック初期35%。TREMOLOは5 Hz。

フォルマント保持、PSOLA/位相ボコーダ、ポリフォニック補正、ノイズ除去、リバーブは未実装です。補間・クロスフェードによる変調感、帯域低下、トランジェントの変化があり、市販の高音質ピッチ補正と同等という検証はありません。実際の声で試聴し、必要ならDSP方式を更新するための実装です。

## 遅延の扱い

|経路・処理|設計上の内訳、未実測|
|---|---|
|PCM3060 ADC + DAC|17.4/fs + 20/fs ≈ 0.779 ms、48 kHzでのデータシート値|
|DMA往復|64フレームの循環バッファで概ね1.333 ms、位相とハードFIFOで差が生じる|
|DRYアナログ往復|約2.1 msを起点とする見積もり。処理期限と実機のクロックを要確認|
|SHIFT/TUNEの読み出し遅延|64～3136サンプル、約1.3～65.3 ms。固定レイテンシではない|
|音程検出|42.7 msの観測窓、分割計算約14.7 ms、追従時定数30 msなどが応答に影響|
|USB|OS・ドライバ・アプリのバッファが追加される|

これらは単純にすべてを足した固定値ではありません。音声通過時間と、音程変化へ追従する時間を別々に測定します。

## ビルド

Ubuntu 24.04系またはDebianで、KiCad 9、pcbnew対応のシステムPython、Inkscape、Cコンパイラ、GNU Arm Embedded GCC/newlib、Python numpy/reportlabを用意します。KiCad 8のCLIをそのまま使うことは想定していません。Ubuntuの標準リポジトリのKiCad版を確認し、必要なら公式案内に従ってKiCad 9を導入します。

```sh
sudo apt-get install gcc-arm-none-eabi libnewlib-arm-none-eabi \
  build-essential git python3-numpy python3-reportlab inkscape
# 別途 KiCad 9 / kicad-footprints / kicad-symbols / python3-pcbnew を導入
bash tools/bootstrap.sh
make test
make firmware
make exports
python3 tools/package_release.py
```

検証時はKiCad 9.0.2、Arm GCC 14.2.1を使用しました。依存コードは固定コミットです。ファームウェアのELF/BIN/HEXは `build/firmware/` に生成されます。Debian系以外のツールチェーンはパスを指定します。

```sh
make -C firmware TOOLCHAIN=/path/to/toolchain/usr \
  NEWLIB=/path/to/toolchain/usr/lib/arm-none-eabi/newlib/thumb/v7e-m+dp/hard
```

`firmware/Makefile` はCortex-M7、hard-float、FPv5-D16を使います。newlibのnosysをリンクするため、ファイルI/Oの未実装を示すリンカ警告が出る場合があります。現ファームウェアにはファイルシステムや標準入出力のサービスはありません。ELFへのリンクとBIN/HEX生成は確認済みです。

`make hardware-check` はERC、DRC、XMLネットリストとPCBパッドの照合、外形、実装面を確認します。`make test` はホスト上のDSPテストとAddressSanitizer/UndefinedBehaviorSanitizerです。STM32エミュレータでのテストではありません。

## SWD書き込み

1. J5のGND、SWDIO、SWCLK、NRST、3.3 V referenceをST-LINKへ接続。
2. 電流制限した5 V電源でUSB-Cから給電。3.3 Vを確認。
3. STM32CubeProgrammerなどで `voice_pitcher.elf` またはHEXを書き込み、verifyを実行。
4. BINを使う場合の書き込み先は **0x08000000**。
5. BOOTを離してRESET。OLED、LED、待機電流を確認後に音声源を接続。

USB DFUの実動作は未確認です。ファームウェア更新用独自ブートローダ、USB経由設定UI、設定永続化はありません。J6は将来のデバッグ用で、現時点ではUART出力しません。

## USBとリアルタイム性

UAC2、48 kHz固定、24 bit packed、2入力/2出力、非同期フルデュプレックスを実装しています。明示的フィードバック、STM32固有IDによるシリアル番号、ホスト構成後の電源切替を含みます。VID 0xCAFE / PID 0x4014は開発用の例示値で、製品配布には適切なVID/PIDへ変更してください。

DMAバッファはD2 SRAMの非キャッシュ領域へ配置し、キャッシュ整合性問題を避けます。OLEDは割り込みによるページ転送です。32フレームあたりの処理期限は666.7 µs、400 MHzでは約266,667サイクルです。SWDで `app_audio_max_cycles`、`audio_overruns` を観測し、USBと表示を動かした最悪条件で余裕を確認してください。サイクル計測コードは用意していますが、実機での期限達成は未測定です。

PC/スマホの互換性、ホストのスリープ/復帰、長時間のクロックドリフト、ケーブル着脱、USB電流規格、アナログのポップ音は試験待ちです。
