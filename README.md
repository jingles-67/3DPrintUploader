# 3D Print Uploader

A desktop application for uploading 3D-printing files to Google Drive,
creating stable public download links and QR codes, and optionally connecting
the result to Beacons.ai.

## Downloads

Open the latest GitHub Release and choose the file for your system:

| System | Release file |
| --- | --- |
| Windows 10/11 | `3D Print Uploader Setup.exe` |
| Ubuntu or Linux Mint | `3D-Print-Uploader-*-Ubuntu-LinuxMint-*.deb` |
| Other Linux distributions | `3D-Print-Uploader-*-Linux-Portable-*.tar.gz` |
| macOS | `3D-Print-Uploader-*-macOS-arm64.dmg` or `*-x86_64.dmg` |
| Source or another platform | `3D-Print-Uploader-*-Source.zip` |

macOS and Windows may warn about an unidentified publisher because the public
packages are not yet signed with paid platform certificates. On macOS,
right-click the app and choose **Open** the first time.

## Features

- Upload `.stl`, `.3mf`, `.step`, `.stp`, `.obj`, `.zip`, or complete folders
- Use each person's own Google Drive account and destination folder
- Generate direct download links and QR codes
- Keep one permanent Google Drive link for a Beacons download button
- Drag and drop files into the desktop interface
- Save local upload history
- Follow a built-in first-run setup tutorial
- Use system, dark, light, or red-and-green themes

## First-time setup

No credentials or personal account information are included in the app.
Open the built-in **Tutorial** after installation and follow these steps:

1. Create or select a Google Cloud project.
2. Enable the Google Drive API.
3. Create an OAuth client with application type **Desktop app**.
4. Download the JSON file.
5. In the app's Settings page, import that JSON file.
6. Sign in to Google, choose a Drive folder, and optionally add a Beacons URL.

The app stores credentials, settings, history, and logs locally for the current
user. Never publish `credentials.json`, `token.json`, `config.json`,
`history.json`, or `app.log`.

## Run from source

Python 3.12 or newer is recommended.

### Windows

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

You can also run `run.bat`.

### Ubuntu or Linux Mint

Install Python's Tk support once, then use the launcher:

```bash
sudo apt install python3 python3-venv python3-tk
chmod +x run.sh
./run.sh
```

### macOS

Install Python 3 from python.org or Homebrew, then run:

```bash
chmod +x run.sh
./run.sh
```

## Local data locations

| Package | Location |
| --- | --- |
| Windows installed app | Beside the per-user installed executable |
| macOS app | `~/Library/Application Support/3D Print Uploader` |
| Linux app | `$XDG_CONFIG_HOME/3d-print-uploader` or `~/.config/3d-print-uploader` |
| Source checkout | Project folder |

## Building packages

PyInstaller must build on the operating system it targets. The included GitHub
Actions workflow builds Windows x64, Linux x64 and ARM64, and macOS Apple
Silicon and Intel automatically without committing large binaries to the
repository.

- Windows: `pyinstaller --noconfirm --clean "3D Print Uploader.spec"`, then
  run `build_installer.bat` with NSIS installed.
- Ubuntu/Linux Mint and portable Linux: `bash packaging/build_linux.sh`.
- macOS DMG: `bash packaging/build_macos.sh` on a Mac.
- Credential-free source archive:
  `python packaging/build_portable.py`.

To publish all files automatically, push a tag matching the version, such as
`v1.2.0`. The **Build installers** workflow creates a GitHub Release and adds
the Windows, Linux, macOS, and source assets after all builds succeed.

## Beacons.ai integration

Beacons does not provide a public link-editing API and its editor can block
automated browsers. The app therefore keeps a stable Google Drive file ID and
replaces that file's contents on later uploads. Add that permanent link to the
Beacons button once; later uploads appear at the same URL automatically.

## Troubleshooting

| Problem | Solution |
| --- | --- |
| Credentials missing | Import your own Desktop-app OAuth JSON in Settings |
| OAuth browser does not open | Check the firewall and default browser |
| Upload fails | Check the internet connection, Drive API, and quota |
| Linux drag-and-drop fails | Install `python3-tk`; source users may also need system TkDND packages |
| macOS blocks the app | Right-click the app and choose **Open** |

See [PRIVACY.md](PRIVACY.md) for the privacy summary.
