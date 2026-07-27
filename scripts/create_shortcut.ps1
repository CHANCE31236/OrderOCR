param(
    [Parameter(Mandatory = $true)][string]$TargetPath,
    [Parameter(Mandatory = $true)][string]$ShortcutPath,
    [string]$WorkingDirectory = "",
    [string]$Description = "订单纸单 OCR、人工审核与 Excel 导出"
)

$source = @"
using System;
using System.Runtime.InteropServices;
using System.Text;

[ComImport]
[Guid("00021401-0000-0000-C000-000000000046")]
internal class ShellLinkClass { }

[ComImport]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
[Guid("000214F9-0000-0000-C000-000000000046")]
internal interface IShellLinkW {
    void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder file, int maxPath, IntPtr findData, uint flags);
    void GetIDList(out IntPtr pidl);
    void SetIDList(IntPtr pidl);
    void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder name, int maxName);
    void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string name);
    void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder dir, int maxPath);
    void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string dir);
    void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder args, int maxPath);
    void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string args);
    void GetHotkey(out short hotkey);
    void SetHotkey(short hotkey);
    void GetShowCmd(out int showCommand);
    void SetShowCmd(int showCommand);
    void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder iconPath, int iconPathLength, out int iconIndex);
    void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string iconPath, int iconIndex);
    void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string path, uint reserved);
    void Resolve(IntPtr hwnd, uint flags);
    void SetPath([MarshalAs(UnmanagedType.LPWStr)] string path);
}

public static class UnicodeShortcut {
    public static void Create(string target, string shortcut, string workingDirectory, string description) {
        var link = (IShellLinkW)new ShellLinkClass();
        link.SetPath(target);
        link.SetWorkingDirectory(workingDirectory);
        link.SetDescription(description);
        link.SetIconLocation(target, 0);
        var file = (System.Runtime.InteropServices.ComTypes.IPersistFile)link;
        file.Save(shortcut, true);
    }
}
"@

Add-Type -TypeDefinition $source -Language CSharp
if (-not (Test-Path -LiteralPath $TargetPath)) {
    throw "目标程序不存在：$TargetPath"
}
if (-not $WorkingDirectory) {
    $WorkingDirectory = Split-Path -Parent $TargetPath
}
[UnicodeShortcut]::Create($TargetPath, $ShortcutPath, $WorkingDirectory, $Description)
if (-not (Test-Path -LiteralPath $ShortcutPath)) {
    throw "快捷方式创建失败：$ShortcutPath"
}

