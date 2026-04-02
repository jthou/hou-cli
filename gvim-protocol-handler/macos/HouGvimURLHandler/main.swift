import Cocoa

/// 最小辅助应用：将 hou-gvim:// 交给 Resources 内的 open-from-url.sh（需先运行 build-app.sh）。
final class AppDelegate: NSObject, NSApplicationDelegate {
    private var didOpenURL = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) { [weak self] in
            guard let self = self else { return }
            if !self.didOpenURL {
                NSApp.terminate(nil)
            }
        }
    }

    func application(_ application: NSApplication, open urls: [URL]) -> Bool {
        didOpenURL = true
        guard let url = urls.first else {
            NSApp.terminate(nil)
            return true
        }
        guard let res = Bundle.main.resourceURL else {
            fputs("HouGvimURLHandler: missing bundle resource URL\n", stderr)
            NSApp.terminate(nil)
            return true
        }
        let script = res.appendingPathComponent("open-from-url.sh").path
        guard FileManager.default.isExecutableFile(atPath: script) else {
            fputs("HouGvimURLHandler: not executable: \(script)\n", stderr)
            NSApp.terminate(nil)
            return true
        }
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/bash")
        p.arguments = [script, url.absoluteString]
        do {
            try p.run()
            p.waitUntilExit()
        } catch {
            fputs("HouGvimURLHandler: \(error)\n", stderr)
        }
        NSApp.terminate(nil)
        return true
    }
}

// NSApplication.delegate 为 weak，须保持强引用
private let gAppDelegate = AppDelegate()

let app = NSApplication.shared
app.delegate = gAppDelegate
app.run()
