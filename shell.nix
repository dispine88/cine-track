{ pkgs ? import <nixpkgs> {} }:
let
  qtLibs = with pkgs; [
    qt5.qtbase
    qt5.qtwayland
    libx11
    libxcb
    libxcb-util
    libxcb-cursor
    libxcb-wm
    libxcb-image
    libxcb-keysyms
    libxcb-render-util
    libxext
    libxrandr
    libxi
    libxcursor
    libxrender
    libxfixes
    libxcomposite
    libxdamage
    libxkbcommon
    wayland
    libGL
    libglvnd
    fontconfig
    freetype
  ];
in
pkgs.mkShell {
  buildInputs = [
    pkgs.python312
    pkgs.python312Packages.pyqt5
    pkgs.python312Packages.requests
    pkgs.python312Packages.pillow
    pkgs.python312Packages.qbittorrent-api
    pkgs.python312Packages.python-dotenv
    pkgs.python312Packages.keyring
    pkgs.qt5.qtbase
    pkgs.qt5.qtwayland
    pkgs.qt5.qtimageformats
    pkgs.mpv
    pkgs.cacert
  ];

  shellHook = ''
    export QT_QPA_PLATFORM_PLUGIN_PATH="${pkgs.qt5.qtbase.bin}/lib/qt-5.15/plugins/platforms"
    export QT_PLUGIN_PATH="${pkgs.qt5.qtbase.bin}/lib/qt-5.15/plugins"
    
    export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath qtLibs}:$LD_LIBRARY_PATH"
    
    export SSL_CERT_FILE="${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt"
  '';
}