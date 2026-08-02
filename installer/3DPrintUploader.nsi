; Nullsoft Scriptable Install System definition for 3D Print Uploader.

Unicode True

!include "MUI2.nsh"
!include "LogicLib.nsh"

!define APP_NAME "3D Print Uploader"
!ifndef APP_VERSION
    !error "APP_VERSION must be supplied by build_installer.bat or release.py"
!endif
!ifndef APP_VERSION_4
    !error "APP_VERSION_4 must be supplied by build_installer.bat or release.py"
!endif
!define APP_PUBLISHER "3D Printing William"
!define APP_EXE "3D Print Uploader.exe"
!define APP_REG_KEY "Software\${APP_PUBLISHER}\${APP_NAME}"
!define UNINSTALL_REG_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
!define PROJECT_DIR "${__FILEDIR__}\.."
!ifndef BUILD_DIST_DIR
    !define BUILD_DIST_DIR "${PROJECT_DIR}\dist"
!endif
!ifndef OUTPUT_DIR
    !define OUTPUT_DIR "${PROJECT_DIR}\dist"
!endif

Name "${APP_NAME}"
OutFile "${OUTPUT_DIR}\3D Print Uploader Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\${APP_NAME}"
InstallDirRegKey HKCU "${APP_REG_KEY}" "InstallDir"
RequestExecutionLevel user
SetCompressor /SOLID lzma
SetDatablockOptimize on
BrandingText "${APP_NAME} ${APP_VERSION}"
Icon "${PROJECT_DIR}\assets\icons\app_icon.ico"
UninstallIcon "${PROJECT_DIR}\assets\icons\app_icon.ico"

VIProductVersion "${APP_VERSION_4}"
VIAddVersionKey /LANG=1033 "ProductName" "${APP_NAME}"
VIAddVersionKey /LANG=1033 "ProductVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "CompanyName" "${APP_PUBLISHER}"
VIAddVersionKey /LANG=1033 "FileDescription" "${APP_NAME} Setup"
VIAddVersionKey /LANG=1033 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Copyright 2026 ${APP_PUBLISHER}"

!define MUI_ABORTWARNING
!define MUI_ICON "${PROJECT_DIR}\assets\icons\app_icon.ico"
!define MUI_UNICON "${PROJECT_DIR}\assets\icons\app_icon.ico"
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "Launch ${APP_NAME}"
!define MUI_FINISHPAGE_LINK "Open Beacons"
!define MUI_FINISHPAGE_LINK_LOCATION "https://beacons.ai/"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

Section "${APP_NAME}" SEC_MAIN
    SectionIn RO
    SetShellVarContext current
    SetOutPath "$INSTDIR"
    SetOverwrite on

    File "${BUILD_DIST_DIR}\${APP_EXE}"
    File "${PROJECT_DIR}\credentials.json.example"

    WriteUninstaller "$INSTDIR\Uninstall.exe"

    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

    WriteRegStr HKCU "${APP_REG_KEY}" "InstallDir" "$INSTDIR"
    WriteRegStr HKCU "${UNINSTALL_REG_KEY}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKCU "${UNINSTALL_REG_KEY}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "${UNINSTALL_REG_KEY}" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKCU "${UNINSTALL_REG_KEY}" "DisplayIcon" "$INSTDIR\${APP_EXE}"
    WriteRegStr HKCU "${UNINSTALL_REG_KEY}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "${UNINSTALL_REG_KEY}" "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
    WriteRegDWORD HKCU "${UNINSTALL_REG_KEY}" "NoModify" 1
    WriteRegDWORD HKCU "${UNINSTALL_REG_KEY}" "NoRepair" 1
    SectionGetSize ${SEC_MAIN} $0
    WriteRegDWORD HKCU "${UNINSTALL_REG_KEY}" "EstimatedSize" $0
SectionEnd

Section "Uninstall"
    SetShellVarContext current

    Delete "$DESKTOP\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"

    Delete "$INSTDIR\${APP_EXE}"
    Delete "$INSTDIR\credentials.json.example"
    Delete "$INSTDIR\Uninstall.exe"

    DeleteRegKey HKCU "${UNINSTALL_REG_KEY}"
    DeleteRegKey HKCU "${APP_REG_KEY}"

    MessageBox MB_YESNO|MB_ICONQUESTION \
        "Also remove your Google credentials, saved sign-in, Beacons settings, Drive folder, upload history, and logs?" \
        /SD IDNO IDNO keep_user_data
    RMDir /r "$INSTDIR"
    Goto uninstall_done

keep_user_data:
    RMDir "$INSTDIR"

uninstall_done:
SectionEnd
