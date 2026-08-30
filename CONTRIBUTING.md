# Contributing Guidelines & Team Workflow

Welcome to the **Foveated Semantic 2.5D LiDAR Mapping** project (SIH 2026).

To enable six engineers to develop high-performance perception and spatial mapping algorithms concurrently without merge conflicts, all team members must follow this workflow.

---

## 1. Branching Strategy

The repository follows a strict feature-branch workflow. **Direct commits to `main` are prohibited.**

### Standard Feature Branches
Each developer has a primary feature branch mapped to their module ownership:

| Developer | Assigned Branch | Module Area |
| :--- | :--- | :--- |
| **Vedant** | `feature/vedant-perception` | Point Cloud Perception (`src/perception/`) |
| **Amulya** | `feature/amulya-preprocessing` | LiDAR Preprocessing (`src/preprocessing/`) |
| **Manashri** | `feature/manashri-foveated-grid` | Foveated Grid Data Structure (`src/foveated_grid/`) |
| **Heet** | `feature/heet-mapping` | 2.5D Elevation & Traversability (`src/mapping/`) |
| **Atharva** | `feature/atharva-integration` | Integration & Visualization (`src/integration/`, `src/visualization/`) |
| **Himisha** | `feature/himisha-evaluation` | Evaluation & Benchmarks (`src/evaluation/`) |

### Creating and Switching to Your Branch
```bash
# Ensure main is up to date
git checkout main
git pull origin main

# Create and checkout your feature branch
git checkout -b feature/<name>-<module>
```

### Working with Git Worktrees (Recommended for Concurrent Development)
If you want to keep separate working directories for testing and cross-module integration without switching branches in your main IDE workspace:
```bash
# Example: create a dedicated worktree for integration
git worktree add ../LiDAR-integration feature/atharva-integration
```

---

## 2. Commit Message Conventions

We adhere to the [Conventional Commits](https://www.conventionalcommits.org/) standard. Each commit message must be structured as follows:

```
<type>(<scope>): <short description>

[optional body explaining motivation and context]
```

### Allowed Types
- `feat`: A new feature or algorithmic capability
- `fix`: A bug fix
- `docs`: Documentation only changes
- `test`: Adding or correcting tests
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `chore`: Changes to build process, dependencies, or auxiliary tools

### Examples
- `feat(preprocessing): add voxel downsampling filter with range clipping`
- `fix(contracts): ensure PointCloudFrame rejects NaN coordinates`
- `test(mapping): add unit test for curb height detection logic`
- `docs(agents): update Atharva's integration handoff guide`

---

## 3. Pre-Pull Request Checklist

Before submitting a Pull Request (PR) to `main`, verify the following:

- [ ] All tests pass locally:
  ```bash
  pytest tests/ -v
  ```
- [ ] No temporary files or datasets are tracked (`git status`).
- [ ] Code conforms to PEP 8 and includes type hints.
- [ ] Any public function or class has an informative docstring.
- [ ] If data contracts or configs are touched, an RFC has been posted and agreed upon.

---

## 4. Pull Request (PR) & Review Expectations

1. **Target Branch:** All PRs must target `main`.
2. **Title:** Use clear conventional commit format (e.g., `feat(foveated_grid): implement multi-ring cell spatial indexer`).
3. **Description:** Explain what was changed, which tests were added, and paste the test execution output.
4. **Code Ownership & Approvals:**
   - Changes inside `src/<module>/` require approval from the assigned module owner.
   - Cross-module integration changes (`src/integration/`) must be reviewed by Atharva.
   - Core contracts (`CONTRACTS.md`, `src/contracts.py`) require at least 2 team reviews.

---

## 5. Interface Change Procedure (RFC Process)

To avoid breaking downstream modules:
1. Open an issue titled `[RFC] Update to <Contract/Config Name>`.
2. Detail the proposed addition, type change, or coordinate requirement.
3. Quantify why the current contract in `CONTRACTS.md` is insufficient.
4. Obtain consensus from all affected module owners before changing `CONTRACTS.md` or `src/contracts.py`.
