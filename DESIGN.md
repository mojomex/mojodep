# mojodep Design Document

mojodep is a tool enabling reproducible builds for any ROS 2 project.

The main hurdles in the ROS 2 ecosystem are the following:

* there is no enforcement of dependency versions in colcon
* old versions of released packages (e.g. in APT) are not usually available
* there can only be one version of an APT dependency installed at a time
* many projects' `.repos` files refer to branches or other non-fixed refs

mojodep tackles these in the following ways:

* generate a `mojodep.lock` file upon successful build, containing exact dependency versions and hashes
* enforce that dependencies match the `mojodep.lock` versions for any successive builds
* resolve, download and build released package versions from [rosdistro][rosdistro]
* generate warnings and/or errors for unresolvable packages and non-fixed dependency versions

The following chapters go into detail on how these measures are implemented.

## rosdistro

Released ROS 2 packages are centrally managed in [rosdistro][rosdistro].
For each distribution (e.g. `humble`, `kilted`, `rolling`), the latest version of each released repository[^1]
is listed, along with metadata such as the repository's release-repository[^2].

Release-repositories contain many sets of data to do with released code and packages, 
but the ones of interest for mojodep are the branches and tags associated with released
source code of each individual package. For example, the [rclcpp-release][rclcpp-release] repository
has (among others) the branches `release/humble/rclcpp`, `release/humble/rclcpp_action`, etc. along with
their versions' tags `release/humble/rclcpp/16.0.13-1` and so on.
The branches contain only the code of that specific package, e.g.

```
- src
- include
- test
- CMakeLists.txt
- package.xml
- ...
```

It is thus possible to, for any valid version of a package, locate its isolated source code, and build that
package from source.

Packages that are not in rosdistro but are in rosdep also exist, and these are mainly system dependencies
that have been made accessible to the ROS 2 ecosystem, e.g. Boost.

[rosdistro]: https://github.com/ros/rosdistro

[^1]: A released repository can contain multiple released packages. For example, the [rclcpp][rclcpp]
      repository contains the `rclcpp`, `rclcpp_action`, `rclcpp_component` and `rclcpp_lifecycle` packages.

[^2]: A release-repository is a repository that contains configuration for ROS 2 release and packaging tools
      such as [bloom][bloom], and branches and tags for each released version of each of the repository's
      packages.

[rclcpp]: https://github.com/ros2/rclcpp
[rclcpp-release]: https://github.com/ros2-gbp/rclcpp-release
[bloom]: https://github.com/ros-infrastructure/bloom