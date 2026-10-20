import subprocess, os, re

REPO = "/root/work/HMCL"
os.chdir(REPO)

def upstream(path):
    return subprocess.run(["git", "show", f"upstream/main:{path}"], capture_output=True, text=True, check=True).stdout

def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def gen_patch(path, new_text, patch_name):
    old = upstream(path)
    write("/tmp/old.java", old)
    write("/tmp/new.java", new_text)
    r = subprocess.run(["diff", "-u", "--label", f"a/{path}", "--label", f"b/{path}", "/tmp/old.java", "/tmp/new.java"],
                       capture_output=True, text=True)
    if r.returncode != 1:
        raise SystemExit(f"no diff for {path} (rc={r.returncode}) {r.stderr}")
    write(os.path.join(".github/workflows/patches", patch_name), r.stdout)
    print(f"wrote {patch_name}: {len(r.stdout.splitlines())} lines")

def must_replace(text, old, new, path):
    if old not in text:
        raise SystemExit(f"pattern not found in {path}:\n{old[:300]}")
    if text.count(old) != 1:
        raise SystemExit(f"pattern not unique in {path}")
    return text.replace(old, new)

# ---------------- AccountListPage ----------------
p = "HMCL/src/main/java/org/jackhuang/hmcl/ui/account/AccountListPage.java"
t = upstream(p)

restricted_block = '''    static final BooleanProperty RESTRICTED = new SimpleBooleanProperty(true);

    static {
        String property = System.getProperty("hmcl.offline.auth.restricted", "auto");

        if ("false".equals(property)
                || "auto".equals(property) && RegionUtils.isIsChinaMainlandMachine()
                || SettingsManager.userSettings().enableOfflineAccountProperty().get())
            RESTRICTED.set(false);
        else
            userSettings().enableOfflineAccountProperty().addListener(new ChangeListener<Boolean>() {
                @Override
                public void changed(ObservableValue<? extends Boolean> o, Boolean oldValue, Boolean newValue) {
                    if (newValue) {
                        userSettings().enableOfflineAccountProperty().removeListener(this);
                        RESTRICTED.set(false);
                    }
                }
            });
    }

'''
t = must_replace(t, restricted_block, "", p)
t = must_replace(t, "        private ChangeListener<Boolean> holder;\n", "", p)

ui_block = '''                    if (RESTRICTED.get()) {
                        VBox wrapper = new VBox(offlineItem, boxAuthServers);
                        wrapper.setPadding(Insets.EMPTY);
                        FXUtils.installFastTooltip(wrapper, i18n("account.login.restricted"));

                        offlineItem.setDisable(true);
                        boxAuthServers.setDisable(true);

                        boxMethods.getChildren().setAll(title, microsoftItem, wrapper);

                        holder = FXUtils.onWeakChange(RESTRICTED, value -> {
                            if (!value) {
                                holder = null;
                                offlineItem.setDisable(false);
                                boxAuthServers.setDisable(false);
                                boxMethods.getChildren().setAll(title, microsoftItem, offlineItem, boxAuthServers);
                            }
                        });
                    } else {
                        boxMethods.getChildren().setAll(title, microsoftItem, offlineItem, boxAuthServers);
                    }
'''
t = must_replace(t, ui_block, "                    boxMethods.getChildren().setAll(title, microsoftItem, offlineItem, boxAuthServers);\n", p)

# drop imports that became unused
for imp in ["import javafx.beans.value.ChangeListener;\n",
            "import org.jackhuang.hmcl.util.RegionUtils;\n",
            "import static org.jackhuang.hmcl.setting.SettingsManager.userSettings;\n"]:
    t = must_replace(t, imp, "", p)

# report leftover import usages for manual check
for sym in ["ChangeListener", "ObservableValue", "RESTRICTED", "RegionUtils", "SimpleBooleanProperty", "BooleanProperty", "Insets", "FXUtils", "VBox"]:
    body = "\n".join(l for l in t.splitlines() if not l.startswith("import "))
    n = len(re.findall(r"\b" + sym + r"\b", body))
    if n == 0:
        print(f"  AccountListPage: {sym} now unused")
write(p, t)
gen_patch(p, t, "AccountListPage.patch")

# ---------------- VersionsPage ----------------
p = "HMCL/src/main/java/org/jackhuang/hmcl/ui/download/VersionsPage.java"
t = upstream(p)
block = '''            if (RegionUtils.isIsChinaMainlandNetwork()) {
                BorderPane wrapper = new BorderPane();

                HintPane hint = new HintPane(MessageDialogPane.MessageType.WARNING);
                hint.setSegment(i18n("download.china"));

                BorderPane.setMargin(hint, new Insets(10, 10, 0, 10));

                wrapper.setTop(hint);

                root.setDisable(true);
                wrapper.setCenter(root);

                this.getChildren().setAll(wrapper);
            } else {
                this.getChildren().setAll(root);
            }
'''
t = must_replace(t, block, "            this.getChildren().setAll(root);\n", p)
for imp in ["import org.jackhuang.hmcl.util.RegionUtils;\n",
            "import org.jackhuang.hmcl.ui.construct.HintPane;\n",
            "import org.jackhuang.hmcl.ui.construct.MessageDialogPane;\n"]:
    if imp in t:
        t = must_replace(t, imp, "", p)
    else:
        print(f"  VersionsPage: import not present: {imp.strip()}")
for sym in ["BorderPane", "Insets", "HintPane", "MessageDialogPane", "RegionUtils", "i18n("]:
    body = "\n".join(l for l in t.splitlines() if not l.startswith("import "))
    n = len(re.findall(re.escape(sym) if sym.endswith("(") else r"\b" + sym + r"\b", body))
    if n == 0:
        print(f"  VersionsPage: {sym} now unused")
write(p, t)
gen_patch(p, t, "VersionsPage.patch")

# ---------------- DownloadListPage ----------------
p = "HMCL/src/main/java/org/jackhuang/hmcl/ui/instances/DownloadListPage.java"
t = upstream(p)
block = '''            if (RegionUtils.isIsChinaMainlandNetwork()) {
                BorderPane wrapper = new BorderPane();

                HintPane hint = new HintPane(MessageDialogPane.MessageType.WARNING);
                hint.setSegment(i18n("download.china"));

                BorderPane.setMargin(hint, new Insets(10, 10, 0, 10));

                wrapper.setTop(hint);

                pane.setDisable(true);
                wrapper.setCenter(pane);

                this.getChildren().setAll(wrapper);
            } else {
                this.getChildren().setAll(pane);
            }
'''
t = must_replace(t, block, "            this.getChildren().setAll(pane);\n", p)
for imp in ["import org.jackhuang.hmcl.util.RegionUtils;\n",
            "import org.jackhuang.hmcl.ui.construct.HintPane;\n",
            "import org.jackhuang.hmcl.ui.construct.MessageDialogPane;\n"]:
    if imp in t:
        t = must_replace(t, imp, "", p)
    else:
        print(f"  DownloadListPage: import not present: {imp.strip()}")
for sym in ["BorderPane", "Insets", "HintPane", "MessageDialogPane", "RegionUtils", "i18n("]:
    body = "\n".join(l for l in t.splitlines() if not l.startswith("import "))
    n = len(re.findall(re.escape(sym) if sym.endswith("(") else r"\b" + sym + r"\b", body))
    if n == 0:
        print(f"  DownloadListPage: {sym} now unused")
write(p, t)
gen_patch(p, t, "DownloadListPage.patch")

print("done")
