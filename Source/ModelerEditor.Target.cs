using UnrealBuildTool;
using System.Collections.Generic;

public class ModelerEditorTarget : TargetRules
{
	public ModelerEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.V6;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_7;

		ExtraModuleNames.AddRange(new string[] { "Modeler" });
	}
}
