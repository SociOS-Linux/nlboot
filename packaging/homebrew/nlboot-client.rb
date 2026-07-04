# frozen_string_literal: true

# Template formula for SocioProphet/homebrew-prophet.
# Do not publish this file directly without replacing url, sha256, version, and target handling.
class NlbootClient < Formula
  desc "SourceOS NLBoot signed boot/recovery client"
  homepage "https://github.com/SociOS-Linux/nlboot"
  version "0.1.0"
  license "MIT"

  on_macos do
    odie "nlboot-client currently targets Linux recovery/operator environments. Use SourceOS devtools or a Linux target."
  end

  on_linux do
    if Hardware::CPU.arm?
      url "https://github.com/SociOS-Linux/nlboot/releases/download/nlboot-client-v0.1.0/nlboot-client-nlboot-client-v0.1.0-aarch64-unknown-linux-gnu.tar.gz"
      sha256 "REPLACE_WITH_AARCH64_SHA256"
    else
      url "https://github.com/SociOS-Linux/nlboot/releases/download/nlboot-client-v0.1.0/nlboot-client-nlboot-client-v0.1.0-x86_64-unknown-linux-gnu.tar.gz"
      sha256 "REPLACE_WITH_X86_64_SHA256"
    end
  end

  def install
    bin.install "nlboot-client"
    doc.install "README.md"
    doc.install "RELEASE_AND_INSTALL.md"
    doc.install "release-manifest.json"
  end

  test do
    assert_match "NLBoot", shell_output("#{bin}/nlboot-client --help")
  end
end
