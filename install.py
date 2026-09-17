"""Install dependencies into the Python interpreter running this script."""
from pathlib import Path
import importlib.util
import subprocess
import sys


def main():
    if sys.version_info < (3, 10):
        print('需要 Python 3.10 或更高版本，请先在 PyCharm 中选择对应解释器。')
        return 1
    root = Path(__file__).resolve().parent
    print('安装依赖到当前解释器：', sys.executable)
    try:
        if importlib.util.find_spec('pip') is None:
            subprocess.run([sys.executable, '-m', 'ensurepip', '--upgrade'], check=True)
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r',
                        str(root / 'requirements.txt')], check=True)
        subprocess.run([sys.executable, '-c', 'import PIL, tkinter'], check=True)
        config = root / 'config.py'
        # Exclusive creation preserves an existing personal configuration.
        try:
            with config.open('x', encoding='utf-8') as output:
                output.write((root / 'config.example.py').read_text(encoding='utf-8-sig'))
        except FileExistsError:
            pass
    except (OSError, subprocess.CalledProcessError) as exc:
        print('安装失败：', exc)
        print('请检查网络、pip 输出，以及当前 Python 是否包含 tkinter。')
        return 1
    print('安装完成。使用同一解释器运行 auto_fishing.py；仅观察请运行 observe.py。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
