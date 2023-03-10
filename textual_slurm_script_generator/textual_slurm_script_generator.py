from textual.app import App, ComposeResult
from textual.containers import Container, Content, Grid, Horizontal
from textual.widgets import (
    Button,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
    Switch,
    TextLog,
)

INPUT_DICT = {
    "job_name": "#SBATCH --job-name={}\t\t# job name\n",
    "partition": "#SBATCH --partition={}\t\t# partition\n",
    "nodes": "#SBATCH --nodes={}\t\t# number of nodes\n",
    "cpu_cores": "#SBATCH --ntasks={}\t\t# number of tasks\n",
    "gpu_cores": "#SBATCH --gres=gpu:{}\t\t# number of gpus per node\n",
    "mem": "#SBATCH --mem={}G\t\t# memory per node\n",
    "email": "#SBATCH --mail-user={}\t\t# email address\n",
    "email_start": "#SBATCH --mail-type=BEGIN\n",
    "email_end": "#SBATCH --mail-type=END\n",
    "email_err": "#SBATCH --mail-type=FAIL\n",
    "wall_time": "#SBATCH --time={}-{}:{}\t\t# wall time D-HH-MM\n",
    "directory": "# Run the job from this directory\ncd {}\n\n",
    "modules": "# Load modules\nmodule load {}\n\n",
    "commands": "# Run the job\nsrun {}\n\n",
}


class DarkSwitch(Horizontal):
    def compose(self) -> ComposeResult:
        yield Switch(value=self.app.dark)
        yield Label("Dark mode toggle")

    def on_mount(self) -> None:
        self.watch(self.app, "dark", self.on_dark_change, init=False)

    def on_dark_change(self, dark: bool) -> None:
        self.query_one(Switch).value = self.app.dark

    def on_switch_changed(self, event: Switch.Changed) -> None:
        self.app.dark = event.value


class EmailSwitches(Horizontal):
    def compose(self) -> ComposeResult:
        yield Switch(value=False, id="email_start")
        yield Label("Job starts   ")
        yield Switch(value=False, id="email_end")
        yield Label("Job ends   ")
        yield Switch(value=False, id="email_err")
        yield Label("Job fails   ")


class FormInput(Container):
    def compose(self) -> ComposeResult:
        yield Static("Job name")
        yield Input(placeholder="Optional: Job name", id="job_name")
        yield Static("Partition (Use 'sinfo' to see available partitions)")
        yield Input(placeholder="gpu, cpu, debug, etc.", id="partition")
        yield Static("Nodes")
        yield Input(
            placeholder="Optional: Number of nodes required", id="nodes"
        )
        yield Static("CPU cores (total)")
        yield Input(placeholder="Number of CPU cores/tasks", id="cpu_cores")
        yield Static("GPUs (per node)")
        yield Input(
            placeholder="Optional: Number of GPUs required per node",
            id="gpu_cores",
        )
        yield Static("Memory required (GB)")
        yield Input(placeholder="Optional: Memory required per node", id="mem")
        yield Static("Notification email")
        yield Input(
            placeholder="Optional: Receive job status notifications",
            id="email",
        )
        yield EmailSwitches(classes="form_horizontal")
        yield Static("Maximum amount of time for job to complete")
        yield Horizontal(
            Input(placeholder="0", id="time_days", classes="time"),
            Label("days   "),
            Input(placeholder="00", id="time_hours", classes="time"),
            Label("hours   "),
            Input(placeholder="00", id="time_mins", classes="time"),
            Label("minutes   "),
            classes="form_horizontal",
        )
        yield Static("Directory to run job from")
        yield Container(
            ListView(
                ListItem(Label("Current directory"), id="current_dir"),
                ListItem(Label("Home directory"), id="home_dir"),
                ListItem(Label("Other"), id="other_dir"),
            ),
            Input(placeholder="If Other, specify here", id="directory"),
            id="listview_container",
        )
        yield Static(
            "Modules to load (Use 'module avail' to see available modules)"
        )
        yield Input(
            placeholder="Optional: Separate modules with comma", id="modules"
        )
        yield Static("Command to run")
        yield Input(placeholder="./executable.x", id="commands")
        yield Horizontal(
            Button("Submit", id="submit", variant="primary"),
            Button("Reset", id="reset", variant="error"),
            classes="buttons",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "reset":
            # clear all inputs
            for input in self.query("Input"):
                input.value = ""
            # clear all switches
            for switch in self.query("EmailSwitches > Switch"):
                switch.value = False
            # clear directory selection
            list_view = self.query_one("FormInput ListView")
            list_view.highlighted_child.highlighted = False
            list_view.index = 0

        elif event.button.id == "submit":
            self.app.generate_script()


class FormOutput(Content):
    def compose(self) -> ComposeResult:
        yield Static("[b]Output preview[/b]")
        yield TextLog()


class AppFooter(Horizontal):
    def compose(self) -> ComposeResult:
        yield DarkSwitch()
        yield Horizontal(
            Button("Save script", id="save", variant="success"),
            Button("Exit", id="exit", variant="error"),
            classes="buttons",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "exit":
            self.app.exit()
        elif event.button.id == "save":
            self.app.save_script()


class SlurmScriptGenerator(App):
    CSS_PATH = "textual_slurm_script_generator.css"
    TITLE = "SLURM Script Generator"
    script = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Grid(
            FormInput(id="form"),
            FormOutput(id="script"),
            id="body",
        )
        yield AppFooter()

    def generate_script(self) -> None:
        # clear previous output
        self.query_one("TextLog").clear()

        script_options = "#!/bin/bash\n"
        script_commands = "\n"

        # query all Input widgets
        inputs = self.query("FormInput Input")
        for input in inputs:
            if input.id == "directory":
                selected = self.query_one(
                    "FormInput ListView"
                ).highlighted_child.id
                if selected == "home_dir":
                    script_commands += INPUT_DICT["directory"].format("$HOME")
                elif selected == "other_dir" and input.value:
                    val = "".join(input.value.split())
                    script_commands += INPUT_DICT["directory"].format(val)
                continue

            if input.value:
                # remove all whitespaces
                val = "".join(input.value.split())
                if (
                    input.id == "gpu_cores"
                    and "gpu"
                    not in self.query_one("FormInput > #partition").value
                ):
                    continue
                elif input.id == "email":
                    script_options += INPUT_DICT["email"].format(val)
                    if self.query_one("#email_start").value:
                        script_options += INPUT_DICT["email_start"]
                    if self.query_one("#email_end").value:
                        script_options += INPUT_DICT["email_end"]
                    if self.query_one("#email_err").value:
                        script_options += INPUT_DICT["email_err"]
                elif input.id.startswith("time_"):
                    if "--time" not in script_options:
                        days = "".join(
                            self.query_one("#time_days").value.split()
                        )
                        days = "0" if len(days) == 0 else days
                        hours = "".join(
                            self.query_one("#time_hours").value.split()
                        )
                        hours = (
                            "00"
                            if len(hours) == 0
                            else ("0" + hours if len(hours) == 1 else hours)
                        )
                        minutes = "".join(
                            self.query_one("#time_mins").value.split()
                        )
                        minutes = (
                            "00"
                            if len(minutes) == 0
                            else (
                                "0" + minutes if len(minutes) == 1 else minutes
                            )
                        )
                        script_options += INPUT_DICT["wall_time"].format(
                            days, hours, minutes
                        )
                elif input.id == "modules":
                    script_commands += INPUT_DICT["modules"].format(
                        val.replace(",", " ")
                    )
                elif input.id == "commands":
                    script_commands += INPUT_DICT["commands"].format(
                        input.value
                    )
                else:
                    script_options += INPUT_DICT[input.id].format(val)
        self.script = script_options + script_commands
        self.query_one("TextLog").write(self.script)

    def save_script(self) -> None:
        if self.script:
            with open("jobscript.sh", "w") as f:
                f.write(self.script)


if __name__ == "__main__":
    app = SlurmScriptGenerator()
    app.run()
