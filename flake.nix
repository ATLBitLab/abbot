{
  description = "A flake for creating a Nix development environment for Abbot";

  # URLs for the Nix inputs to use
  inputs = {
    # The largest repository of Nix packages
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    # Helper functions for using flakes
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          # Packages included in the environment
          buildInputs = with pkgs.python311Packages; [
            aiohttp
            aiosignal
            annotated-types
            anyio
            appnope
            asn1crypto
            asttokens
            async-timeout
            attrs
            backcall
            cachetools
            certifi
            cffi
            charset-normalizer
            click
            coincurve
            cryptography
            dataclasses-json
            decorator
            distro
            dnspython
            executing
            frozenlist
            google-api-core
            google-api-python-client
            google-auth
            google-auth-httplib2
            googleapis-common-protos
            greenlet
            h11
            httpcore
            httplib2
            httpx
            idna
            ipython
            jedi
            jsonpatch
            jsonpointer
            langchain
            langsmith
            loguru
            markdown-it-py
            marshmallow
            matplotlib-inline
            mdurl
            multidict
            mypy-extensions
            # nostr
            # nostr-sdk @ git+https://github.com/atlbitlab/nostr-sdk-ffi-bindings-python.git@master
            numpy
            openai
            packaging
            parso
            pexpect
            pickleshare
            pinecone-client
            pip
            prompt-toolkit
            protobuf
            ptyprocess
            pure-eval
            pyasn1
            pyasn1-modules
            pycparser
            pydantic
            pydantic-core
            pygments
            pymongo
            pyparsing
            pypng
            python-dateutil
            python-dotenv
            python-telegram-bot
            pytz
            pyyaml
            qrcode
            regex
            requests
            rich
            rsa
            secp256k1
            six
            sniffio
            sqlalchemy
            stack-data
            tenacity
            tiktoken
            tlv8
            tornado
            tqdm
            traitlets
            typer
            typing-inspect
            typing-extensions
            uritemplate
            urllib3
            wcwidth
            websocket-client
            yarl
          ]
          ++ [ pkgs.python311 ];

          # Environment variables can be set here
          MY_VARIABLE = "moo";

          # Run when the shell is started up
          shellHook = with pkgs; ''
              echo " `${cowsay}/bin/cowsay $MY_VARIABLE`"
              echo "You are now in a Nix development shell."
              echo "You can exit with the 'exit' command."
          '';
        };
      });
}
