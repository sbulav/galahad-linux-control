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
      in
      {
        packages.default = pkgs.rustPlatform.buildRustPackage {
          pname = "galahad-linux-control";
          version = "0.1.0";
          src = ./.;

          cargoLock.lockFile = ./Cargo.lock;

          nativeBuildInputs = [
            pkgs.pkg-config
            pkgs.makeWrapper
          ];

          buildInputs = [
            pkgs.libusb1
          ];

          postInstall = ''
            wrapProgram $out/bin/glc \
              --prefix PATH : ${pkgs.lib.makeBinPath [ pkgs.ffmpeg ]} \
              --set FONTCONFIG_FILE ${pkgs.fontconfig.out}/etc/fonts/fonts.conf \
              --set FONTCONFIG_PATH ${pkgs.fontconfig.out}/etc/fonts \
              --prefix XDG_DATA_DIRS : ${pkgs.noto-fonts}/share
          '';
        };

        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/glc";
        };

        devShells.default = pkgs.mkShell {
          buildInputs = [
            pkgs.cargo
            pkgs.rustc
            pkgs.rustfmt
            pkgs.clippy
            pkgs.pkg-config
            pkgs.libusb1
            pkgs.ffmpeg
            pkgs.fontconfig
            pkgs.noto-fonts
          ];

           shellHook = ''
             export FONTCONFIG_FILE=${pkgs.fontconfig.out}/etc/fonts/fonts.conf
             export FONTCONFIG_PATH=${pkgs.fontconfig.out}/etc/fonts
             echo "Galahad II LCD dev environment ready!"
             echo "Run: cargo run -- [OPTIONS]"
           '';
        };
      }
    );
}
