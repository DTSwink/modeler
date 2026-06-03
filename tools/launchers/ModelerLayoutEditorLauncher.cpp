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

bool windowTitleStartsWith(HWND window, const std::wstring& prefix)
{
	wchar_t titleBuffer[512] = {};
	const int titleLength = GetWindowTextW(window, titleBuffer, 512);
	if (titleLength <= 0)
	{
		return false;
	}

	const std::wstring title(titleBuffer, titleLength);
	return title.rfind(prefix, 0) == 0;
}

BOOL CALLBACK findEditorWindowCallback(HWND window, LPARAM userData)
{
	if (!IsWindowVisible(window))
	{
		return TRUE;
	}

	if (!windowTitleStartsWith(window, kWindowTitle))
	{
		return TRUE;
	}

	*reinterpret_cast<HWND*>(userData) = window;
	return FALSE;
}

HWND findExistingEditorWindow()
{
	HWND foundWindow = nullptr;
	EnumWindows(findEditorWindowCallback, reinterpret_cast<LPARAM>(&foundWindow));
	return foundWindow;
}

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

void bringExistingWindowToFront(HWND window)
{
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
}

bool getFileLastWriteTime(const std::filesystem::path& path, FILETIME* result)
{
	WIN32_FILE_ATTRIBUTE_DATA data = {};
	if (!GetFileAttributesExW(path.c_str(), GetFileExInfoStandard, &data))
	{
		return false;
	}

	*result = data.ftLastWriteTime;
	return true;
}

bool getWindowProcessCreationTime(HWND window, FILETIME* result)
{
	DWORD processId = 0;
	GetWindowThreadProcessId(window, &processId);
	if (processId == 0)
	{
		return false;
	}

	HANDLE processHandle = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, processId);
	if (!processHandle)
	{
		return false;
	}

	FILETIME creationTime = {};
	FILETIME exitTime = {};
	FILETIME kernelTime = {};
	FILETIME userTime = {};
	const BOOL ok = GetProcessTimes(processHandle, &creationTime, &exitTime, &kernelTime, &userTime);
	CloseHandle(processHandle);

	if (!ok)
	{
		return false;
	}

	*result = creationTime;
	return true;
}

bool shouldLaunchFreshEditor(HWND existingWindow, const std::filesystem::path& scriptPath)
{
	FILETIME scriptLastWriteTime = {};
	FILETIME processCreationTime = {};
	if (!getFileLastWriteTime(scriptPath, &scriptLastWriteTime))
	{
		return false;
	}

	if (!getWindowProcessCreationTime(existingWindow, &processCreationTime))
	{
		return false;
	}

	return CompareFileTime(&scriptLastWriteTime, &processCreationTime) > 0;
}
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int)
{
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

	if (HWND existingWindow = findExistingEditorWindow())
	{
		if (!shouldLaunchFreshEditor(existingWindow, scriptPath))
		{
			bringExistingWindowToFront(existingWindow);
			return 0;
		}
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
