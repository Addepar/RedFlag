<a name="readme-top"></a>

<div align="center">
  <a href="https://github.com/Addepar/RedFlag">
    <img src="https://raw.githubusercontent.com/Addepar/RedFlag/main/docs/images/RedFlag-Logo.png" alt="RedFlag" height="100">
  </a>


[![Python][python-shield]][python-url]
[![Contributors][contributors-shield]][contributors-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]<br />
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]

RedFlag leverages AI to determine high-risk code changes. 
Run it in batch mode to scope manual security testing of release candidates, 
or run it in your CI pipelines to flag PRs and add the appropriate reviewers. 
Despite being a security tool, RedFlag can be leveraged for almost any team 
as it's configuration makes it infinitely flexible.
<br />
<a href="https://addepar.com/blog/introducing-redflag-using-ai-to-scale-addepar-s-offensive-security-team"><strong>Read the blog post »</strong></a>
<br />
<br />
<a href="https://opensource.addepar.com/RedFlag/">View Sample Report</a>
·
<a href="https://github.com/Addepar/RedFlag/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
·
<a href="https://github.com/Addepar/RedFlag/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>

</div>

<details>
<summary><strong>Table of Contents</strong></summary>
<ul>
    <li><a href="#batch-mode">Batch Mode</a></li>
    <li><a href="#ci-mode">CI Mode</a></li>
    <li><a href="#evaluation-mode">Evaluation Mode</a></li>
    <li><a href="#advanced-configuration">Advanced Configuration</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
</ul>
</details>

---

# Batch Mode

RedFlag is able to analyze a large number of commits in a single run.
These commits can be specified using commit hashes, branch names, or tags.
This is useful for scoping manual security testing of logical groups of code,
such as release candidates.

## Workflow

![Batch Workflow][batch-workflow]

## Getting Started

### Installation

##### Use a Virtual Environment

1. Create a virtual environment:
   ```shell
   python -m venv redflag-venv
   source redflag-venv/bin/activate
   ```
   
1. Install RedFlag:
   ```shell
   pip install addepar-redflag
   ```

Alternatively, if you'd like to use Poetry, clone the repo and use `poetry install` and then `poetry run redflag`.

### Setup Credentials

Credentials can be set using...
1. Environment variables 
1. A `.env` file
1. CLI parameters
1. Configuration file (This is not recommended for security reasons!)

##### AWS Credentials

RedFlag uses [Boto3-Compatible Credentials](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html) using **Profiles** or **Env Vars**.
Ensure that your AWS IAM policy has `InvokeModel` and `InvokeModelWithResponseStream` permissions to [Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/security_iam_service-with-iam.html). 
Lastly, *make sure you've [requested the necessary Claude models](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)!*

##### GitHub PAT

Use a [Personal Access Token](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token) with
`repo` permissions. Set the token as an environment variable:

```shell
export RF_GITHUB_TOKEN=your-token-here
```

##### Jira API Token *(Optional)*
First, set a Jira URL (`https://your-org.atlassian.net`) in the configuration file (`jira_url`), as a CLI parameter (`--jira-url`), or as an environment variable (`RF_JIRA_URL`).

Then create a [Jira API Token](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/) and
set it as an environment variable:

```shell
export RF_JIRA_USER=your-username-here
export RF_JIRA_TOKEN=your-token-here
```

### Usage

Here are some examples on how to run RedFlag in batch mode.

```shell
# Using branch names:
redflag --repo YourOrg/SomeRepo --from main --to dev
# Using commit hashes:
redflag --repo YouOrg/SomeRepo --from a1b2c3 --to d4e5f6
# With a custom configuration file:
redflag --config custom-config.yml
```

## Report Output

By default, RedFlag produces an HTML report that can be opened in a browser.

<a href="https://opensource.addepar.com/RedFlag/">
   <img src="https://raw.githubusercontent.com/Addepar/RedFlag/main/docs/images/Report-Animated.gif">
</a>

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

# CI Mode

RedFlag can be run in CI pipelines to flag PRs and add the appropriate reviewers.
This mode uses GitHub Actions to run RedFlag on every PR and post a comment if
the PR requires a review.

[![CI Mode][docs-ci-mode]][docs-ci-mode-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

# Evaluation Mode

RedFlag can be run in evaluation mode to evaluate the performance of the AI model using your own custom
dataset. This mode is useful for understanding how the model and prompts perform on your codebase and aids in security
risk evaluation.

[![Evaluation Mode][docs-eval-mode]][docs-eval-mode-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

# Advanced Configuration

## Order of Precedence

1. CLI Parameters
1. Environment Variables
1. Configuration File
1. Default Values

On each execution, RedFlag will load the configuration in the order of precedence above and then
output a table that shows the final configuration and where each parameter was set.

## Configuration Options and Defaults

The following table shows configuration options for each parameter:

#### General Settings

| Parameter                                                                             | CLI Param | Env Var | Config File | Default |
|---------------------------------------------------------------------------------------|-----------|---------|-------------|---------|
| [Configuration File](https://github.com/Addepar/RedFlag/blob/main/config.sample.yaml) | --config  | -       | -           | -       |
| Repository                                                                            | --repo    | RF_REPO | repo        | -       |
| Branch/Commit From                                                                    | --from    | RF_FROM | from        | -       |
| Branch/Commit To                                                                      | --to      | RF_TO   | to          | -       |

#### Integration Settings

| Parameter                                                                                                                           | CLI Param      | Env Var          | Config File   | Default |
|-------------------------------------------------------------------------------------------------------------------------------------|----------------|------------------|---------------|---------|
| [GitHub Token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) | --github-token | RF_GITHUB_TOKEN  | github_token  | -       |
| Jira URL                                                                                                                            | --jira-url     | RF_JIRA_URL      | jira.url      | -       |
| Jira Username                                                                                                                       | --jira-user    | RF_JIRA_USER     | jira.user     | -       |
| [Jira Token](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)                    | --jira-token   | RF_JIRA_TOKEN    | jira.token    | -       |

#### LLM Settings

| Parameter                                                                                                          | CLI Param          | Env Var             | Config File                | Default                                   |
|--------------------------------------------------------------------------------------------------------------------|--------------------|---------------------|----------------------------|-------------------------------------------|
| Debug LLM                                                                                                          | --debug-llm        | -                   | -                          | `False`                                   |
| [Bedrock Model ID](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html)                            | --bedrock-model-id | RF_BEDROCK_MODEL_ID | bedrock.model_id           | `anthropic.claude-3-sonnet-20240229-v1:0` |
| [Bedrock Profile](https://docs.aws.amazon.com/cli/v1/userguide/cli-configure-files.html)                           | --bedrock-profile  | RF_BEDROCK_PROFILE  | bedrock.profile            | -                                         |
| [Bedrock Region](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.RegionsAndAvailabilityZones.html) | --bedrock-region   | RF_BEDROCK_REGION   | bedrock.region             | -                                         |
| Review Prompt (Role)                                                                                               | -                  | -                   | prompts.review.role        | Security review (see `sample.config.yaml`)       |
| Review Prompt (Question)                                                                                           | -                  | -                   | prompts.review.question    | Security review (see `sample.config.yaml`)       |
| Test Plan Prompt (Role)                                                                                            | -                  | -                   | prompts.test_plan.role     | Security review (see `sample.config.yaml`)       |
| Test Plan Prompt (Question)                                                                                        | -                  | -                   | prompts.test_plan.question | Security review (see `sample.config.yaml`)       |

#### Input/Output Settings

| Parameter                 | CLI Param                | Env Var        | Config File             | Default   |
|---------------------------|--------------------------|----------------|-------------------------|-----------|
| Output Directory          | --output-dir             | RF_OUTPUT_DIR  | output_dir              | `results` |
| Maximum Commits           | --max-commits            | RF_MAX_COMMITS | max_commits             | `0` (∞)   |
| Don't Output HTML         | --no-output-html         | -              | -                       | -         |
| Don't Output JSON         | --no-output-json         | -              | -                       | -         |
| Don't Show Progress Bar   | --no-progress-bar        | -              | -                       | -         |
| Don't Strip HTML Comments | --no-strip-html-comments | -              | -                       | -         |
| Filter Commit Titles      | -                        | -              | filter_commits.title    | -         |
| Filter Commit Users       | -                        | -              | filter_commits.user     | -         |
| Strip Description Lines   | -                        | -              | strip_description_lines | -         |

#### Evaluation Parameters (`eval` Command)

| Parameter                                                                                               | CLI Param  | Env Var          | Config File  | Default |
|---------------------------------------------------------------------------------------------------------|------------|------------------|--------------|---------|
| [Evaluation Dataset](https://github.com/Addepar/RedFlag/wiki/Evaluation-Mode#building-a-custom-dataset) | --dataset  | RF_DATASET       | dataset | - |

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. 
Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. 
You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## License

Distributed under the MIT License. See [`LICENSE.md`](https://github.com/Addepar/RedFlag?tab=MIT-1-ov-file#readme) for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

---

## Contact

Say hi to Addepar Security Engineering at [security-engineering@addepar.com](mailto:security-engineering@addepar.com).


<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->

[python-shield]: https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white
[python-url]: https://www.python.org/
[contributors-shield]: https://img.shields.io/github/contributors/Addepar/RedFlag.svg?style=for-the-badge
[contributors-url]: https://github.com/Addepar/RedFlag/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/Addepar/RedFlag.svg?style=for-the-badge
[forks-url]: https://github.com/Addepar/RedFlag/network/members
[stars-shield]: https://img.shields.io/github/stars/Addepar/RedFlag.svg?style=for-the-badge
[stars-url]: https://github.com/Addepar/RedFlag/stargazers
[issues-shield]: https://img.shields.io/github/issues/Addepar/RedFlag.svg?style=for-the-badge
[issues-url]: https://github.com/Addepar/RedFlag/issues
[license-shield]: https://img.shields.io/github/license/Addepar/RedFlag.svg?style=for-the-badge
[license-url]: https://github.com/Addepar/RedFlag/blob/main/LICENSE.md
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/company/addepar

[batch-workflow]: https://raw.githubusercontent.com/Addepar/RedFlag/main/docs/images/Batch-Workflow.png
[docs-ci-mode]: https://img.shields.io/badge/Read%20More-How%20To%20Use%20RedFlag%20In%20CI%20Mode-blue?style=for-the-badge&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAAXNSR0IArs4c6QAAAERlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQAAAABAAAAMKADAAQAAAABAAAAMAAAAADbN2wMAAABcUlEQVRoBe1ZQU7DMBBsOPMC3gISDwDxAr5BJe5I/Ki3gkS58ROO9MKFdJZmLyOysWIzUNiVVs527Rl7JrnUi8V/iL7vr5CPyC1SFQ9NtMVu71U7Zp7qAwDQlLd4R94gT6pBCwCM0KJgajwFGPbaWCzjmW27e8o2B3gbwD6Vx/Ozg3/DuHEZHNvraDyKmugdU/+D6pZle2xXAuPBvkJ+BvuIl8hf9xF30Ttgu4/6ot6m67qzMa6pb8DXneNhhXz1H4Tj6Wwuc8BiDGDfHe+PrSv9vQS/1IFSTvm8PIBcciJMB0gQeZkOyCUnwnSABJGX6YBcciJMB0gQeZkOyCUnwnSABJGX6YBcciJMB0gQeZkOyCUnwnSABJGX6YBcciJMB0gQefnnHdiapPibW3IzM8e+KQdeBtDrOeA/vgbKXw6XDF/ekZVcQNQcogQ/vCMzcoDcYbit2UjtWtyRTe4z5MAhLpBrpF9841EWT+HmDr25A8AdiN2uwvv8AAAAAElFTkSuQmCC
[docs-ci-mode-url]: https://github.com/Addepar/RedFlag/wiki/CI-Mode
[docs-eval-mode]: https://img.shields.io/badge/Read%20More-How%20To%20Use%20RedFlag%20In%20Evaluation%20Mode-blue?style=for-the-badge&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAYAAABXAvmHAAAAAXNSR0IArs4c6QAAAERlWElmTU0AKgAAAAgAAYdpAAQAAAABAAAAGgAAAAAAA6ABAAMAAAABAAEAAKACAAQAAAABAAAAMKADAAQAAAABAAAAMAAAAADbN2wMAAABcUlEQVRoBe1ZQU7DMBBsOPMC3gISDwDxAr5BJe5I/Ki3gkS58ROO9MKFdJZmLyOysWIzUNiVVs527Rl7JrnUi8V/iL7vr5CPyC1SFQ9NtMVu71U7Zp7qAwDQlLd4R94gT6pBCwCM0KJgajwFGPbaWCzjmW27e8o2B3gbwD6Vx/Ozg3/DuHEZHNvraDyKmugdU/+D6pZle2xXAuPBvkJ+BvuIl8hf9xF30Ttgu4/6ot6m67qzMa6pb8DXneNhhXz1H4Tj6Wwuc8BiDGDfHe+PrSv9vQS/1IFSTvm8PIBcciJMB0gQeZkOyCUnwnSABJGX6YBcciJMB0gQeZkOyCUnwnSABJGX6YBcciJMB0gQeZkOyCUnwnSABJGX6YBcciJMB0gQefnnHdiapPibW3IzM8e+KQdeBtDrOeA/vgbKXw6XDF/ekZVcQNQcogQ/vCMzcoDcYbit2UjtWtyRTe4z5MAhLpBrpF9841EWT+HmDr25A8AdiN2uwvv8AAAAAElFTkSuQmCC
[docs-eval-mode-url]: https://github.com/Addepar/RedFlag/wiki/Evaluation-Mode
