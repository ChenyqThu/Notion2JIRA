api/2/issueExpand all methods
Create issue
POST /rest/api/2/issue
Creates an issue or a sub-task from a JSON representation.

The fields that can be set on create, in either the fields parameter or the update parameter can be determined using the /rest/api/2/issue/createmeta resource. If a field is not configured to appear on the create screen, then it will not be in the createmeta, and a field validation error will occur if it is submitted.

Creating a sub-task is similar to creating a regular issue, with two important differences:

the issueType field must correspond to a sub-task issue type (you can use /issue/createmeta to discover sub-task issue types), and
you must provide a parent field in the issue create request containing the id or key of the parent issue.
Request
Example
{
    "update": {
        "worklog": [
            {
                "add": {
                    "timeSpent": "60m",
                    "started": "2011-07-05T11:05:00.000+0000"
                }
            }
        ]
    },
    "fields": {
        "project": {
            "id": "10000"
        },
        "summary": "something's wrong",
        "issuetype": {
            "id": "10000"
        },
        "assignee": {
            "name": "homer"
        },
        "reporter": {
            "name": "smithers"
        },
        "priority": {
            "id": "20000"
        },
        "labels": [
            "bugfix",
            "blitz_test"
        ],
        "timetracking": {
            "originalEstimate": "10",
            "remainingEstimate": "5"
        },
        "security": {
            "id": "10000"
        },
        "versions": [
            {
                "id": "10000"
            }
        ],
        "environment": "environment",
        "description": "description",
        "duedate": "2011-03-11",
        "fixVersions": [
            {
                "id": "10001"
            }
        ],
        "components": [
            {
                "id": "10000"
            }
        ],
        "customfield_30000": [
            "10000",
            "10002"
        ],
        "customfield_80000": {
            "value": "red"
        },
        "customfield_20000": "06/Jul/11 3:25 PM",
        "customfield_40000": "this is a text field",
        "customfield_70000": [
            "jira-administrators",
            "jira-software-users"
        ],
        "customfield_60000": "jira-software-users",
        "customfield_50000": "this is a text area. big text.",
        "customfield_10000": "09/Jun/81"
    }
}
Schema
Responses
Status 201 - application/jsonReturns a link to the created issue.
Example
{
    "id": "10000",
    "key": "TST-24",
    "self": "http://www.example.com/jira/rest/api/2/issue/10000"
}
Schema
Status 400Returned if the input is invalid (e.g. missing required fields, invalid field values, and so forth).
Example
{
    "errorMessages": [
        "Field 'priority' is required"
    ],
    "errors": {}
}


Add comment
POST /rest/api/2/issue/{issueIdOrKey}/comment
Adds a new comment to an issue.

Request
query parameters
parameter	type	description
expand	string	
optional flags: renderedBody (provides body rendered in HTML)

Example
{
    "body": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Pellentesque eget venenatis elit. Duis eu justo eget augue iaculis fermentum. Sed semper quam laoreet nisi egestas at posuere augue semper.",
    "visibility": {
        "type": "role",
        "value": "Administrators"
    }
}
Schema
{
    "id": "https://docs.atlassian.com/jira/REST/schema/comment#",
    "title": "Comment",
    "type": "object",
    "properties": {
        "id": {
            "type": "string"
        },
        "author": {
            "$ref": "#/definitions/user"
        },
        "body": {
            "type": "string"
        },
        "renderedBody": {
            "type": "string"
        },
        "updateAuthor": {
            "$ref": "#/definitions/user"
        },
        "created": {
            "type": "string"
        },
        "updated": {
            "type": "string"
        },
        "visibility": {
            "title": "Visibility",
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "group",
                        "role"
                    ]
                },
                "value": {
                    "type": "string"
                }
            },
            "additionalProperties": false
        },
        "properties": {
            "type": "array",
            "items": {
                "title": "Entity Property",
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string"
                    },
                    "value": {}
                },
                "additionalProperties": false
            }
        }
    },
    "definitions": {
        "user": {
            "title": "User",
            "type": "object",
            "properties": {
                "name": {
                    "type": "string"
                },
                "key": {
                    "type": "string"
                },
                "emailAddress": {
                    "type": "string"
                },
                "avatarUrls": {
                    "type": "object",
                    "patternProperties": {
                        ".+": {
                            "type": "string"
                        }
                    },
                    "additionalProperties": false
                },
                "displayName": {
                    "type": "string"
                },
                "active": {
                    "type": "boolean"
                },
                "timeZone": {
                    "type": "string"
                }
            },
            "additionalProperties": false,
            "required": [
                "active"
            ]
        }
    },
    "additionalProperties": false
}
Responses
Status 201Returned if add was successful
Example
{
    "self": "http://www.example.com/jira/rest/api/2/issue/10010/comment/10000",
    "id": "10000",
    "author": {
        "self": "http://www.example.com/jira/rest/api/2/user?username=fred",
        "name": "fred",
        "displayName": "Fred F. User",
        "active": false
    },
    "body": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Pellentesque eget venenatis elit. Duis eu justo eget augue iaculis fermentum. Sed semper quam laoreet nisi egestas at posuere augue semper.",
    "updateAuthor": {
        "self": "http://www.example.com/jira/rest/api/2/user?username=fred",
        "name": "fred",
        "displayName": "Fred F. User",
        "active": false
    },
    "created": "2017-01-03T15:22:51.591+0000",
    "updated": "2017-01-03T15:22:51.591+0000",
    "visibility": {
        "type": "role",
        "value": "Administrators"
    }
}
Schema
{
    "id": "https://docs.atlassian.com/jira/REST/schema/comment#",
    "title": "Comment",
    "type": "object",
    "properties": {
        "self": {
            "type": "string"
        },
        "id": {
            "type": "string"
        },
        "author": {
            "$ref": "#/definitions/user"
        },
        "body": {
            "type": "string"
        },
        "renderedBody": {
            "type": "string"
        },
        "updateAuthor": {
            "$ref": "#/definitions/user"
        },
        "created": {
            "type": "string"
        },
        "updated": {
            "type": "string"
        },
        "visibility": {
            "title": "Visibility",
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "group",
                        "role"
                    ]
                },
                "value": {
                    "type": "string"
                }
            },
            "additionalProperties": false
        },
        "properties": {
            "type": "array",
            "items": {
                "title": "Entity Property",
                "type": "object",
                "properties": {
                    "key": {
                        "type": "string"
                    },
                    "value": {}
                },
                "additionalProperties": false
            }
        }
    },
    "definitions": {
        "user": {
            "title": "User",
            "type": "object",
            "properties": {
                "self": {
                    "type": "string"
                },
                "name": {
                    "type": "string"
                },
                "key": {
                    "type": "string"
                },
                "emailAddress": {
                    "type": "string"
                },
                "avatarUrls": {
                    "type": "object",
                    "patternProperties": {
                        ".+": {
                            "type": "string"
                        }
                    },
                    "additionalProperties": false
                },
                "displayName": {
                    "type": "string"
                },
                "active": {
                    "type": "boolean"
                },
                "timeZone": {
                    "type": "string"
                }
            },
            "additionalProperties": false,
            "required": [
                "active"
            ]
        }
    },
    "additionalProperties": false
}
Status 400Returned if the input is invalid (e.g. missing required fields, invalid values, and so forth).