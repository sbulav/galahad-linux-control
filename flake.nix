{
  description = "Lian Li Galahad II LCD control for Linux";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        python = pkgs.python3.withPackages (ps: with ps; [
           pyusb
           pillow
           psutil
           pytest
           av
         ]);
      in
      {
        packages.default = pkgs.writeShellScriptBin "glc" ''
          export PATH="${pkgs.ffmpeg}/bin:$PATH"
          export FONTCONFIG_FILE=${pkgs.fontconfig.out}/etc/fonts/fonts.conf
          export FONTCONFIG_PATH=${pkgs.fontconfig.out}/etc/fonts
          exec ${python}/bin/python ${./glc.py} "$@"
        '';

        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/glc";
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            python
            pkgs.libusb1
            pkgs.ffmpeg
            pkgs.noto-fonts
          ];

           shellHook = ''
             export FONTCONFIG_FILE=${pkgs.fontconfig.out}/etc/fonts/fonts.conf
             echo "Galahad II LCD dev environment ready!"
             echo "Run: python glc.py"
           '';
        };
      }
    );
}
