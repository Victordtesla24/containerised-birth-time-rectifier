[{
	"resource": "/Users/Shared/cursor/containerised-birth-time-rectifier/ai_service/api/services/openai/service.py",
	"owner": "_generated_diagnostic_collection_name_#1",
	"code": {
		"value": "reportOptionalMemberAccess",
		"target": {
			"$mid": 1,
			"path": "/microsoft/pyright/blob/main/docs/configuration.md",
			"scheme": "https",
			"authority": "github.com",
			"fragment": "reportOptionalMemberAccess"
		}
	},
	"severity": 8,
	"message": "\"post\" is not a known attribute of \"None\"",
	"source": "Pylance",
	"startLineNumber": 115,
	"startColumn": 46,
	"endLineNumber": 115,
	"endColumn": 50,
	"modelVersionId": 1
},{
	"resource": "/Users/Shared/cursor/containerised-birth-time-rectifier/ai_service/api/services/openai/service.py",
	"owner": "_generated_diagnostic_collection_name_#1",
	"code": {
		"value": "reportReturnType",
		"target": {
			"$mid": 1,
			"path": "/microsoft/pyright/blob/main/docs/configuration.md",
			"scheme": "https",
			"authority": "github.com",
			"fragment": "reportReturnType"
		}
	},
	"severity": 8,
	"message": "Expression of type \"ClientResponse\" is incompatible with return type \"Dict[str, Any]\"\n  \"ClientResponse\" is incompatible with \"Dict[str, Any]\"",
	"source": "Pylance",
	"startLineNumber": 119,
	"startColumn": 36,
	"endLineNumber": 119,
	"endColumn": 44,
	"modelVersionId": 1
}]
[{
	"resource": "/Users/Shared/cursor/containerised-birth-time-rectifier/ai_service/api/services/questionnaire_service.py",
	"owner": "_generated_diagnostic_collection_name_#1",
	"code": {
		"value": "reportArgumentType",
		"target": {
			"$mid": 1,
			"path": "/microsoft/pyright/blob/main/docs/configuration.md",
			"scheme": "https",
			"authority": "github.com",
			"fragment": "reportArgumentType"
		}
	},
	"severity": 8,
	"message": "Argument of type \"Coroutine[Any, Any, OpenAIService | None]\" cannot be assigned to parameter \"openai_service\" of type \"OpenAIService | None\" in function \"__init__\"\n  Type \"Coroutine[Any, Any, OpenAIService | None]\" is incompatible with type \"OpenAIService | None\"\n    \"Coroutine[Any, Any, OpenAIService | None]\" is incompatible with \"OpenAIService\"\n    \"Coroutine[Any, Any, OpenAIService | None]\" is incompatible with \"None\"",
	"source": "Pylance",
	"startLineNumber": 768,
	"startColumn": 55,
	"endLineNumber": 768,
	"endColumn": 69,
	"modelVersionId": 5
}]
