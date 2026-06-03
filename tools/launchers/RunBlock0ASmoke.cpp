#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>

#include <filesystem>
#include <string>

namespace
{
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
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int)
{
	const std::filesystem::path root = executableDirectory();
	const std::filesystem::path batchPath = root / L"BuildAndTestCore.bat";

	if (!std::filesystem::exists(batchPath))
	{
		return showError(L"Could not find BuildAndTestCore.bat next to the launcher.");
	}

	const HINSTANCE result = ShellExecuteW(
		nullptr,
		L"open",
		batchPath.c_str(),
		nullptr,
		root.c_str(),
		SW_SHOWNORMAL);

	if (reinterpret_cast<INT_PTR>(result) <= 32)
	{
		return showError(L"Windows could not launch BuildAndTestCore.bat.");
	}

	return 0;
}
