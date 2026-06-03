#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>

#include <filesystem>
#include <string>

namespace
{
constexpr wchar_t kWindowTitle[] = L"Modeler Layout Editor";
constexpr wchar_t kPythonRelativePath[] = L"..\\stepper\\.tools\\python310\\pythonw.exe";
constexpr wchar_t kScriptName[] = L"ModelerLayoutEditor.pyw";

std::filesystem::path executableDirectory()
{
	wchar_t buffer[MAX_PATH] = {};
	const DWORD length = GetModuleFileNameW(nullptr, buffer, MAX_PATH);
	return std::filesystem::path(std::wstring(buffer, length)).parent_path();
}

int showError(const wchar_t* message)
{
	MessageBoxW(nullptr, message, L"Modeler Launcher", MB_OK | MB_ICONERROR);
	return 1;
}

bool bringExistingWindowToFront()
{
	HWND window = FindWindowW(nullptr, kWindowTitle);
	if (!window)
	{
		return false;
	}

	if (IsIconic(window))
	{
		ShowWindow(window, SW_RESTORE);
	}
	else
	{
		ShowWindow(window, SW_SHOW);
	}

	SetForegroundWindow(window);
	BringWindowToTop(window);
	SetActiveWindow(window);
	SetFocus(window);
	return true;
}
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int)
{
	if (bringExistingWindowToFront())
	{
		return 0;
	}

	const std::filesystem::path root = executableDirectory();
	const std::filesystem::path pythonPath = root / kPythonRelativePath;
	const std::filesystem::path scriptPath = root / kScriptName;

	if (!std::filesystem::exists(scriptPath))
	{
		return showError(L"Could not find ModelerLayoutEditor.pyw next to the launcher.");
	}

	if (!std::filesystem::exists(pythonPath))
	{
		return showError(L"Could not find pythonw.exe for the Modeler editor.");
	}

	const std::wstring arguments = L"\"" + scriptPath.wstring() + L"\"";

	const HINSTANCE result = ShellExecuteW(
		nullptr,
		L"open",
		pythonPath.c_str(),
		arguments.c_str(),
		root.c_str(),
		SW_SHOWNORMAL);

	if (reinterpret_cast<INT_PTR>(result) <= 32)
	{
		return showError(L"Windows could not launch the Modeler layout editor.");
	}

	return 0;
}
